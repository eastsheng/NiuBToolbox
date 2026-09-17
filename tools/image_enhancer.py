from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

try:
    from pillow_heif import register_heif_opener

    register_heif_opener(thumbnails=False)
except ImportError:
    pass


class ImageEnhancer:
    """Run local Real-ESRGAN NCNN inference for photo and artwork upscaling."""

    MODEL_NAMES = {"photo": "realesrgan-x4plus", "art": "realesrgan-x4plus-anime"}
    DENOISE = {"none": 0, "low": 2, "medium": 4, "high": 7}

    @staticmethod
    def default_engine_path() -> Path:
        base = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
        onnx = base / "models" / "RealESRGAN_x4plus.onnx"
        ncnn = base / "models" / "realesrgan-ncnn-vulkan" / "realesrgan-ncnn-vulkan.exe"
        return onnx if onnx.is_file() else ncnn

    @classmethod
    def resolve_engine(cls, configured_path: str | None = None) -> Path:
        candidates = []
        if configured_path:
            selected = Path(configured_path)
            if selected.is_dir():
                candidates.extend((selected / "RealESRGAN_x4plus.onnx", selected / "realesrgan-ncnn-vulkan.exe"))
            else:
                candidates.append(selected)
        candidates.append(cls.default_engine_path())
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        raise FileNotFoundError(f"Real-ESRGAN engine not found: {candidates[0]}")

    @staticmethod
    def _available_path(source: Path) -> Path:
        candidate = source.with_name(f"{source.stem}_ai_enhanced.png")
        index = 2
        while candidate.exists():
            candidate = source.with_name(f"{source.stem}_ai_enhanced_{index}.png")
            index += 1
        return candidate

    @staticmethod
    def _model_directory(engine: Path, model_name: str) -> Path:
        for directory in (engine.parent / "models", engine.parent):
            if (directory / f"{model_name}.param").is_file() and (directory / f"{model_name}.bin").is_file():
                return directory
        raise FileNotFoundError(f"Real-ESRGAN model files not found: {model_name}.param / {model_name}.bin")

    @staticmethod
    def _prepare_input(source: Path, target: Path, noise: str) -> tuple[tuple[int, int], Image.Image | None]:
        with Image.open(source) as opened:
            if getattr(opened, "is_animated", False):
                raise ValueError("Animated images are not supported by AI enhancement.")
            image = ImageOps.exif_transpose(opened)
            image.load()
            original_size = image.size
            alpha = image.getchannel("A") if "A" in image.getbands() else None
            rgb = np.asarray(image.convert("RGB"))

        strength = ImageEnhancer.DENOISE.get(noise, 0)
        if strength:
            bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            bgr = cv2.fastNlMeansDenoisingColored(bgr, None, strength, strength, 7, 21)
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        Image.fromarray(rgb).save(target, "PNG")
        return original_size, alpha

    @staticmethod
    def _run_onnx(model: Path, prepared: Path, rendered: Path, scale: int) -> None:
        rgb = np.asarray(Image.open(prepared).convert("RGB"), dtype=np.float32) / 255.0
        height, width = rgb.shape[:2]
        native_scale, tile, overlap = 4, 128, 12
        output = np.empty((height * native_scale, width * native_scale, 3), dtype=np.float32)
        net = cv2.dnn.readNetFromONNX(str(model))
        for top in range(0, height, tile):
            for left in range(0, width, tile):
                bottom, right = min(top + tile, height), min(left + tile, width)
                outer_top, outer_left = max(0, top - overlap), max(0, left - overlap)
                outer_bottom, outer_right = min(height, bottom + overlap), min(width, right + overlap)
                patch = rgb[outer_top:outer_bottom, outer_left:outer_right]
                blob = np.transpose(patch, (2, 0, 1))[None].astype(np.float32)
                net.setInput(blob)
                predicted = net.forward()
                if predicted.ndim == 4:
                    predicted = predicted[0]
                predicted = np.transpose(predicted, (1, 2, 0))
                crop_top = (top - outer_top) * native_scale
                crop_left = (left - outer_left) * native_scale
                crop_bottom = crop_top + (bottom - top) * native_scale
                crop_right = crop_left + (right - left) * native_scale
                output[top * native_scale:bottom * native_scale, left * native_scale:right * native_scale] = predicted[crop_top:crop_bottom, crop_left:crop_right]
        output = np.clip(output * 255.0, 0, 255).astype(np.uint8)
        image = Image.fromarray(output, "RGB")
        if scale == 2:
            image = image.resize((width * 2, height * 2), Image.Resampling.LANCZOS)
        image.save(rendered, "PNG")

    def enhance(
        self,
        source_path: str,
        engine_path: str | None,
        style: str = "photo",
        noise: str = "low",
        scale: int = 4,
        output_dir: str | Path | None = None,
    ) -> tuple[Path, tuple[int, int], tuple[int, int]]:
        source = Path(source_path)
        engine = self.resolve_engine(engine_path)
        scale = scale if scale in (2, 4) else 4

        with tempfile.TemporaryDirectory(prefix="niub-upscale-") as temp_dir:
            temp = Path(temp_dir)
            prepared = temp / "input.png"
            rendered = temp / "output.png"
            original_size, alpha = self._prepare_input(source, prepared, noise)
            if engine.suffix.lower() == ".onnx":
                selected_model = engine
                if style == "art":
                    anime_model = engine.with_name("RealESRGAN_x4plus_anime_6B.onnx")
                    if anime_model.is_file(): selected_model = anime_model
                self._run_onnx(selected_model, prepared, rendered, scale)
            else:
                model_name = self.MODEL_NAMES.get(style, self.MODEL_NAMES["photo"])
                model_dir = self._model_directory(engine, model_name)
                command = [
                    str(engine), "-i", str(prepared), "-o", str(rendered),
                    "-n", model_name, "-s", str(scale), "-t", "128", "-m", str(model_dir), "-f", "png",
                ]
                result = subprocess.run(
                    command, cwd=str(engine.parent), capture_output=True, text=True,
                    errors="replace", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=False,
                )
                if result.returncode != 0 or not rendered.is_file():
                    details = (result.stderr or result.stdout or "Real-ESRGAN returned no output").strip()
                    raise RuntimeError(details)

            with Image.open(rendered) as generated:
                output_image = generated.convert("RGB")
                output_image.load()
            if alpha is not None:
                alpha = alpha.resize(output_image.size, Image.Resampling.LANCZOS)
                output_image.putalpha(alpha)
            output = self._available_path(Path(output_dir) / source.name if output_dir else source)
            output_image.save(output, "PNG", optimize=True, compress_level=6)
            return output, original_size, output_image.size
