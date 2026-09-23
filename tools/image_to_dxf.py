from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

try:
    from pillow_heif import register_heif_opener
    register_heif_opener(thumbnails=False)
except ImportError:
    pass


class ImageToDxfConverter:
    """Vectorize raster image contours into a portable ASCII DXF file."""

    @staticmethod
    def _load_gray(source: Path) -> np.ndarray:
        with Image.open(source) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGBA")
            background = Image.new("RGBA", image.size, "white")
            background.alpha_composite(image)
            return np.asarray(background.convert("L"), dtype=np.uint8)

    @staticmethod
    def _dxf_header(width_mm: float, height_mm: float) -> list[str]:
        return [
            "0", "SECTION", "2", "HEADER", "9", "$ACADVER", "1", "AC1015",
            "9", "$INSUNITS", "70", "4",
            "9", "$EXTMIN", "10", "0.000000", "20", "0.000000", "30", "0.000000",
            "9", "$EXTMAX", "10", f"{width_mm:.6f}", "20", f"{height_mm:.6f}", "30", "0.000000",
            "0", "ENDSEC",
            "0", "SECTION", "2", "TABLES", "0", "TABLE", "2", "LAYER", "70", "1",
            "0", "LAYER", "2", "OUTLINE", "70", "0", "62", "7", "6", "CONTINUOUS",
            "0", "ENDTAB", "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES",
        ]

    @staticmethod
    def read_polylines(path: str | Path) -> list[list[tuple[float, float]]]:
        """Read LWPOLYLINE vertices from a generated ASCII DXF for preview."""
        raw = Path(path).read_text(encoding="ascii", errors="ignore").splitlines()
        pairs = [(raw[index].strip(), raw[index + 1].strip()) for index in range(0, len(raw) - 1, 2)]
        polylines: list[list[tuple[float, float]]] = []
        current: list[tuple[float, float]] | None = None
        pending_x: float | None = None
        for code, value in pairs:
            if code == "0":
                if current:
                    polylines.append(current)
                current = [] if value == "LWPOLYLINE" else None
                pending_x = None
            elif current is not None and code == "10":
                try: pending_x = float(value)
                except ValueError: pending_x = None
            elif current is not None and code == "20" and pending_x is not None:
                try: current.append((pending_x, float(value)))
                except ValueError: pass
                pending_x = None
        if current:
            polylines.append(current)
        return polylines

    @staticmethod
    def read_bounds(path: str | Path) -> tuple[float, float, float, float] | None:
        raw = Path(path).read_text(encoding="ascii", errors="ignore").splitlines()
        pairs = [(raw[index].strip(), raw[index + 1].strip()) for index in range(0, len(raw) - 1, 2)]
        values: dict[str, list[float]] = {"$EXTMIN": [], "$EXTMAX": []}
        active: str | None = None
        for code, value in pairs:
            if code == "9": active = value if value in values else None
            elif active and code in ("10", "20"):
                try: values[active].append(float(value))
                except ValueError: return None
                if len(values[active]) == 2: active = None
        if len(values["$EXTMIN"]) == 2 and len(values["$EXTMAX"]) == 2:
            return values["$EXTMIN"][0], values["$EXTMAX"][0], values["$EXTMIN"][1], values["$EXTMAX"][1]
        return None

    def convert(
        self, source_path: str, output_dir: str | Path, mode: str = "outline",
        detail: int = 70, width_mm: float = 100.0,
    ) -> tuple[Path, int]:
        source = Path(source_path)
        if not source.is_file():
            raise ValueError("Please select a valid image.")
        gray = self._load_gray(source)
        height, width = gray.shape
        if width < 2 or height < 2:
            raise ValueError("The image is too small to vectorize.")

        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        if mode == "silhouette":
            _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            border = np.concatenate((binary[0], binary[-1], binary[:, 0], binary[:, -1]))
            if float(border.mean()) > 127:
                binary = cv2.bitwise_not(binary)
            contours, _ = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
        else:
            median = float(np.median(blurred))
            lower = int(max(10, 0.66 * median)); upper = int(min(245, max(lower + 20, 1.33 * median)))
            edges = cv2.Canny(blurred, lower, upper, L2gradient=True)
            contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)

        detail = max(1, min(100, int(detail)))
        scale = max(1.0, float(width_mm)) / width
        epsilon_ratio = 0.0005 + ((100 - detail) / 99.0) * 0.018
        min_length = max(4.0, min(width, height) * 0.004)
        polylines: list[np.ndarray] = []
        for contour in contours:
            perimeter = cv2.arcLength(contour, True)
            if perimeter < min_length:
                continue
            simplified = cv2.approxPolyDP(contour, perimeter * epsilon_ratio, True).reshape(-1, 2)
            if len(simplified) >= 3:
                polylines.append(simplified)
        if not polylines:
            raise ValueError("No usable contours were found. Try another extraction mode or a clearer image.")

        lines = self._dxf_header(float(width_mm), height * scale)
        for points in polylines:
            lines.extend(("0", "LWPOLYLINE", "8", "OUTLINE", "90", str(len(points)), "70", "1"))
            for x, y in points:
                lines.extend(("10", f"{x * scale:.6f}", "20", f"{(height - y) * scale:.6f}"))
        lines.extend(("0", "ENDSEC", "0", "EOF"))

        destination_dir = Path(output_dir)
        destination_dir.mkdir(parents=True, exist_ok=True)
        output = destination_dir / f"{source.stem}.dxf"
        output.write_text("\n".join(lines) + "\n", encoding="ascii")
        return output, len(polylines)
