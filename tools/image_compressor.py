from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image, ImageOps, ImageSequence

try:
    from pillow_heif import register_heif_opener

    register_heif_opener(thumbnails=False)
except ImportError:
    # Pillow still handles every built-in format when the optional HEIF codec
    # has not yet been installed.
    pass


class ImageCompressor:
    """Compress an image without changing its pixel dimensions."""

    @staticmethod
    def _available_path(source: Path, suffix: str) -> Path:
        candidate = source.with_name(f"{source.stem}_compressed{suffix}")
        index = 2
        while candidate.exists():
            candidate = source.with_name(f"{source.stem}_compressed_{index}{suffix}")
            index += 1
        return candidate

    def compress(self, source_path: str, output_format: str, quality: int, output_dir: str | Path | None = None) -> tuple[Path, int, int]:
        source = Path(source_path)
        with Image.open(source) as opened:
            source_format = (opened.format or source.suffix.lstrip(".")).upper()
            selected_format = output_format.upper()
            if selected_format == "ORIGINAL":
                selected_format = source_format
            animated = bool(getattr(opened, "is_animated", False))
            durations = [frame.info.get("duration", opened.info.get("duration", 100)) for frame in ImageSequence.Iterator(opened)]
            frames = [ImageOps.exif_transpose(frame).convert("RGBA") for frame in ImageSequence.Iterator(opened)]
            image = frames[0] if animated else ImageOps.exif_transpose(opened)
            image.load()
            icc_profile = opened.info.get("icc_profile")
            exif = opened.getexif()
            loop = opened.info.get("loop", 0)
            if 274 in exif:
                exif[274] = 1

        suffixes = {
            "JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp", "GIF": ".gif",
            "TIFF": ".tiff", "BMP": ".bmp", "ICO": ".ico", "HEIF": ".heic",
            "AVIF": ".avif", "TGA": ".tga", "PPM": ".ppm",
        }
        suffix = source.suffix if output_format.upper() == "ORIGINAL" else suffixes[selected_format]
        output_base = Path(output_dir) / source.name if output_dir else source
        output = self._available_path(output_base, suffix)
        common = {"icc_profile": icc_profile} if icc_profile else {}

        if selected_format == "JPEG":
            if image.mode in ("RGBA", "LA"):
                background = Image.new("RGB", image.size, "white")
                background.paste(image, mask=image.getchannel("A"))
                image = background
            elif image.mode != "RGB":
                image = image.convert("RGB")
            if exif:
                common["exif"] = exif.tobytes()
            image.save(output, "JPEG", quality=quality, progressive=True, subsampling=0, **common)
        elif selected_format == "WEBP":
            if animated:
                frames[0].save(
                    output, "WEBP", save_all=True, append_images=frames[1:],
                    duration=durations, loop=loop, quality=quality, method=6, **common
                )
            else:
                image.save(output, "WEBP", quality=quality, method=6, **common)
        else:
            if selected_format == "PNG":
                if animated:
                    frames[0].save(
                        output, "PNG", save_all=True, append_images=frames[1:],
                        duration=durations, loop=loop, optimize=True, compress_level=9, **common
                    )
                else:
                    image.save(output, "PNG", optimize=True, compress_level=9, **common)
            elif selected_format == "GIF" and animated:
                frames[0].save(
                    output, "GIF", save_all=True, append_images=frames[1:],
                    duration=durations, loop=loop, optimize=True
                )
            elif selected_format == "GIF":
                image.convert("P", palette=Image.Palette.ADAPTIVE).save(output, "GIF", optimize=True)
            elif selected_format == "TIFF":
                image.save(
                    output, "TIFF", compression="tiff_adobe_deflate",
                    save_all=animated, append_images=frames[1:] if animated else [], **common
                )
            elif selected_format in ("HEIF", "AVIF"):
                image.save(
                    output, selected_format, quality=quality,
                    save_all=animated, append_images=frames[1:] if animated else [], **common
                )
            else:
                image.save(output, selected_format, **common)

        original_size = source.stat().st_size
        if selected_format == source_format and output.stat().st_size >= original_size:
            # Some already-optimized or uncompressed formats cannot be made
            # smaller without changing format or dimensions. Never return a
            # file larger than the source in that case.
            shutil.copyfile(source, output)
        return output, original_size, output.stat().st_size
