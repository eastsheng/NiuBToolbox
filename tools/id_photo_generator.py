from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageFilter, ImageOps

try:
    from pillow_heif import register_heif_opener

    register_heif_opener(thumbnails=False)
except ImportError:
    pass


class IdPhotoGenerator:
    """Extract a portrait with MODNet and composite it over a chosen background."""

    OUTPUT_SIZES = {
        "one_inch": (295, 413),
        "two_inch": (413, 579),
    }

    @staticmethod
    def default_model_path() -> Path:
        base = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
        return base / "models" / "modnet_photographic.onnx"

    @classmethod
    def resolve_model(cls, configured_path: str | None = None) -> Path:
        candidates = [Path(configured_path)] if configured_path else []
        candidates.append(cls.default_model_path())
        for candidate in candidates:
            if candidate.is_file(): return candidate
        raise FileNotFoundError(f"MODNet portrait model not found: {candidates[0]}")

    @staticmethod
    def _available_path(source: Path) -> Path:
        candidate = source.with_name(f"{source.stem}_id_photo.png")
        index = 2
        while candidate.exists():
            candidate = source.with_name(f"{source.stem}_id_photo_{index}.png")
            index += 1
        return candidate

    @staticmethod
    def _background(size: tuple[int, int], primary: str, secondary: str, gradient: bool) -> Image.Image:
        width, height = size
        first = np.array(Image.new("RGB", (1, 1), primary))[0, 0].astype(np.float32)
        if not gradient:
            return Image.new("RGB", size, tuple(first.astype(np.uint8)))
        second = np.array(Image.new("RGB", (1, 1), secondary))[0, 0].astype(np.float32)
        weight = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None, None]
        colors = first[None, None, :] * (1.0 - weight) + second[None, None, :] * weight
        array = np.broadcast_to(colors, (height, width, 3)).astype(np.uint8).copy()
        return Image.fromarray(array, "RGB")

    @staticmethod
    def _predict_matte(image: Image.Image, model_path: Path) -> Image.Image:
        rgb = np.asarray(image.convert("RGB"))
        height, width = rgb.shape[:2]
        reference = 512
        if width >= height:
            resized_width = reference
            resized_height = max(32, int(height / width * reference) // 32 * 32)
        else:
            resized_height = reference
            resized_width = max(32, int(width / height * reference) // 32 * 32)
        resized = cv2.resize(rgb, (resized_width, resized_height), interpolation=cv2.INTER_AREA)
        tensor = resized.astype(np.float32) / 127.5 - 1.0
        blob = np.transpose(tensor, (2, 0, 1))[None]
        net = cv2.dnn.readNetFromONNX(str(model_path))
        net.setInput(blob)
        matte = net.forward()
        matte = np.squeeze(matte)
        matte = cv2.resize(matte, (width, height), interpolation=cv2.INTER_CUBIC)
        matte = np.clip(matte, 0.0, 1.0)
        alpha = Image.fromarray((matte * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(0.7))
        return alpha

    def generate(
        self, source_path: str, model_path: str | None, primary: str,
        secondary: str, gradient: bool, output_dir: str | Path | None = None,
        photo_size: str = "one_inch",
    ) -> Path:
        source = Path(source_path)
        model = self.resolve_model(model_path)
        with Image.open(source) as opened:
            if getattr(opened, "is_animated", False): raise ValueError("Animated images are not supported.")
            portrait = ImageOps.exif_transpose(opened).convert("RGB")
            portrait.load()
        target_size = self.OUTPUT_SIZES.get(photo_size, self.OUTPUT_SIZES["one_inch"])
        portrait = ImageOps.fit(portrait, target_size, Image.Resampling.LANCZOS, centering=(0.5, 0.5))
        matte = self._predict_matte(portrait, model)
        background = self._background(portrait.size, primary, secondary, gradient)
        result = Image.composite(portrait, background, matte)
        output = self._available_path(Path(output_dir) / source.name if output_dir else source)
        result.save(output, "PNG", optimize=True, compress_level=6)
        return output
