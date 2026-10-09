from __future__ import annotations

import csv
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps


def detect_axes(rgb: np.ndarray) -> dict[str, float] | None:
    """Locate the long horizontal/vertical plot axes without inventing tick values."""
    height, width = rgb.shape[:2]
    if width < 80 or height < 80:
        return None
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 60, 160)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 75,
                            minLineLength=max(50, int(min(width, height) * .28)),
                            maxLineGap=max(5, int(min(width, height) * .025)))
    if lines is None:
        return None
    horizontal, vertical = [], []
    for x1, y1, x2, y2 in lines.reshape(-1, 4):
        dx, dy = abs(x2 - x1), abs(y2 - y1)
        if dx > width * .3 and dy <= max(3, dx * .025) and height * .45 < y1 < height * .96:
            horizontal.append((dx, (y1 + y2) / 2, min(x1, x2), max(x1, x2)))
        if dy > height * .3 and dx <= max(3, dy * .025) and width * .04 < x1 < width * .55:
            vertical.append((dy, (x1 + x2) / 2, min(y1, y2), max(y1, y2)))
    candidates = []
    for _, y, left, right in horizontal:
        for _, x, top, bottom in vertical:
            if left - width * .03 <= x <= right + width * .03 and top - height * .03 <= y <= bottom + height * .03:
                score = (right - left) / width + (bottom - top) / height
                score += .25 if abs(x - left) < width * .08 else 0
                score += .25 if abs(y - bottom) < height * .08 else 0
                candidates.append((score, x, y, right, top))
    if not candidates:
        return None
    _, x, y, right, top = max(candidates)
    if right - x < width * .25 or y - top < height * .25:
        return None
    return {"xmin": float(x), "xmax": float(right), "ymin": float(y), "ymax": float(top)}


def detect_axis_ticks(rgb: np.ndarray, axes: dict[str, float]) -> dict[str, float]:
    """Choose the second tick from each end, counting the axis boundary as first."""
    height, width = rgb.shape[:2]
    x0, x1, y0, y1 = (axes[key] for key in ("xmin", "xmax", "ymin", "ymax"))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    dark = gray < 110
    left, right, bottom, top = map(round, (x0, x1, y0, y1))
    # Vertical ticks point upward from the X axis; horizontal ticks point
    # rightward from the Y axis. Avoid the axis pixels and any outer frame.
    x_margin = max(15, int((x1 - x0) * .035))
    y_margin = max(15, int((y0 - y1) * .045))
    x_start, x_end = max(0, left + x_margin), min(width, right - x_margin)
    y_start, y_end = max(0, top + y_margin), min(height, bottom - y_margin)
    x_ticks: list[float] = []
    y_ticks: list[float] = []
    if x_end > x_start and bottom >= 6:
        strip = dark[max(0, bottom - 18):bottom - 2, x_start:x_end]
        root = dark[max(0, bottom - 5):bottom - 2, x_start:x_end]
        if strip.size and root.size:
            mask = (strip.sum(axis=0) >= 2) & (root.sum(axis=0) >= 1)
            x_ticks = _run_centers(mask, x_start)
    if y_end > y_start and left + 8 < width:
        strip = dark[y_start:y_end, max(0, left + 3):min(width, left + 18)]
        root = dark[y_start:y_end, max(0, left + 3):min(width, left + 7)]
        if strip.size and root.size:
            mask = (strip.sum(axis=1) >= 3) & (root.sum(axis=1) >= 1)
            y_ticks = _run_centers(mask, y_start)
    ticks = {}
    if len(x_ticks) >= 2 and x_ticks[-1] - x_ticks[0] > (x1 - x0) * .25:
        ticks.update(xmin=x_ticks[0], xmax=x_ticks[-1])
    if len(y_ticks) >= 2 and y_ticks[-1] - y_ticks[0] > (y0 - y1) * .25:
        ticks.update(ymax=y_ticks[0], ymin=y_ticks[-1])
    return ticks


def _run_centers(mask: np.ndarray, offset: int) -> list[float]:
    indices = np.flatnonzero(mask)
    if not len(indices):
        return []
    groups = np.split(indices, np.flatnonzero(np.diff(indices) > 1) + 1)
    return [float(offset + (group[0] + group[-1]) / 2) for group in groups if len(group) <= 5]


def load_rgb(path: str | Path) -> np.ndarray:
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        return np.asarray(image)


def pixel_to_value(point: tuple[float, float], roi: tuple[int, int, int, int],
                   limits: tuple[float, float, float, float], x_log: bool = False,
                   y_log: bool = False,
                   calibration: dict[str, float] | None = None) -> tuple[float, float]:
    left, top, right, bottom = roi
    x_min, x_max, y_min, y_max = limits
    anchors = calibration or {"xmin": left, "xmax": right, "ymin": bottom, "ymax": top}
    if (right <= left or bottom <= top or x_min == x_max or y_min == y_max
            or anchors["xmin"] == anchors["xmax"] or anchors["ymin"] == anchors["ymax"]):
        raise ValueError("Invalid plot bounds or axis limits.")
    fx = (point[0] - anchors["xmin"]) / (anchors["xmax"] - anchors["xmin"])
    fy = (point[1] - anchors["ymin"]) / (anchors["ymax"] - anchors["ymin"])
    if x_log:
        if x_min <= 0 or x_max <= 0: raise ValueError("Log X axis limits must be positive.")
        x = float(np.exp(np.log(x_min) + fx * (np.log(x_max) - np.log(x_min))))
    else:
        x = x_min + fx * (x_max - x_min)
    if y_log:
        if y_min <= 0 or y_max <= 0: raise ValueError("Log Y axis limits must be positive.")
        y = float(np.exp(np.log(y_min) + fy * (np.log(y_max) - np.log(y_min))))
    else:
        y = y_min + fy * (y_max - y_min)
    return x, y


def value_to_pixel(value: tuple[float, float], roi: tuple[int, int, int, int],
                   limits: tuple[float, float, float, float], x_log: bool = False,
                   y_log: bool = False,
                   calibration: dict[str, float] | None = None) -> tuple[float, float]:
    left, top, right, bottom = roi
    x_min, x_max, y_min, y_max = limits
    anchors = calibration or {"xmin": left, "xmax": right, "ymin": bottom, "ymax": top}
    if anchors["xmin"] == anchors["xmax"] or anchors["ymin"] == anchors["ymax"]:
        raise ValueError("Axis calibration points must be distinct.")
    x, y = value
    if x_log:
        fx = (np.log(x) - np.log(x_min)) / (np.log(x_max) - np.log(x_min))
    else:
        fx = (x - x_min) / (x_max - x_min)
    if y_log:
        fy = (np.log(y) - np.log(y_min)) / (np.log(y_max) - np.log(y_min))
    else:
        fy = (y - y_min) / (y_max - y_min)
    return float(anchors["xmin"] + fx * (anchors["xmax"] - anchors["xmin"])), float(anchors["ymin"] + fy * (anchors["ymax"] - anchors["ymin"]))


def detect_points(rgb: np.ndarray, roi: tuple[int, int, int, int],
                  sample: tuple[int, int], mode: str = "points",
                  tolerance: int = 30, marker_size: int = 7,
                  curve_step: int = 5,
                  plot_axes: dict[str, float] | None = None) -> list[tuple[float, float]]:
    height, width = rgb.shape[:2]
    left, top, right, bottom = roi
    if not (0 <= left < right <= width and 0 <= top < bottom <= height):
        raise ValueError("Invalid image bounds.")
    sx, sy = sample
    if not (left <= sx < right and top <= sy < bottom):
        raise ValueError("Choose a series color inside the plot area.")
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    target = lab[sy, sx].astype(np.int32)
    crop = lab[top:bottom, left:right].astype(np.int32)
    delta = crop - target
    distance = np.sqrt(np.sum(delta * delta, axis=2, dtype=np.int32))
    mask = np.asarray(distance <= max(5, min(100, tolerance)), dtype=np.uint8) * 255
    if mode == "points":
        plot_left, plot_top, plot_right, plot_bottom = left, top, right, bottom
        if plot_axes:
            plot_left = max(left, round(plot_axes["xmin"] + 5))
            plot_right = min(right, round(plot_axes["xmax"] - 5))
            plot_top = max(top, round(plot_axes["ymax"] + 5))
            plot_bottom = min(bottom, round(plot_axes["ymin"] - 5))
        radius = max(1, marker_size // 3)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (radius * 2 + 1, radius * 2 + 1))
        cleaned = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        count, labels, stats, centers = cv2.connectedComponentsWithStats(cleaned, 8)
        result = []
        min_area = max(3, int(marker_size * marker_size * 0.1))
        max_extent = max(8, marker_size * 3)
        for label in range(1, count):
            x, y, w, h, area = stats[label]
            if area < min_area or w > max_extent or h > max_extent:
                continue
            if x <= 0 or y <= 0 or x + w >= right - left or y + h >= bottom - top:
                continue
            cx, cy = centers[label]
            image_x, image_y = float(left + cx), float(top + cy)
            if not (plot_left <= image_x < plot_right and plot_top <= image_y < plot_bottom):
                continue
            if plot_axes and image_x > plot_left + .55 * (plot_right - plot_left) and image_y < plot_top + .32 * (plot_bottom - plot_top):
                mid_x, mid_y = round(cx), round(cy)
                nearby = mask[max(0, mid_y - 2):min(mask.shape[0], mid_y + 3),
                              max(0, mid_x - 30):min(mask.shape[1], mid_x + 31)]
                columns = np.flatnonzero(np.any(nearby > 0, axis=0))
                text_area = rgb[max(0, round(image_y) - 12):min(height, round(image_y) + 13),
                                min(width, round(image_x) + 25):min(width, round(image_x) + 145)]
                dark_text = int(np.count_nonzero(cv2.cvtColor(text_area, cv2.COLOR_RGB2GRAY) < 120)) if text_area.size else 0
                if (len(columns) and columns[-1] - columns[0] > marker_size * 4) or dark_text > 80:
                    continue  # colored legend swatch plus its horizontal line
            result.append((image_x, image_y))
        return sorted(result)
    if mode == "curve":
        # Thin anti-aliased line pixels are much lighter than filled markers.
        curve_threshold = 150 if target[0] < 80 else 100
        curve_mask = np.asarray(distance <= max(curve_threshold, tolerance), dtype=np.uint8)
        if plot_axes:
            plot_left = max(0, min(curve_mask.shape[1], round(plot_axes["xmin"] - left + 10)))
            plot_right = max(0, min(curve_mask.shape[1], round(plot_axes["xmax"] - left - 4)))
            plot_top = max(0, min(curve_mask.shape[0], round(plot_axes["ymax"] - top + 4)))
            plot_bottom = max(0, min(curve_mask.shape[0], round(plot_axes["ymin"] - top - 4)))
            if plot_right > plot_left and plot_bottom > plot_top:
                curve_mask[:plot_top] = 0; curve_mask[plot_bottom:] = 0
                curve_mask[:, :plot_left] = 0; curve_mask[:, plot_right:] = 0
        seed_x, seed_y = sx - left, sy - top
        if not (0 <= seed_x < curve_mask.shape[1] and 0 <= seed_y < curve_mask.shape[0]):
            return []
        if not curve_mask[seed_y, seed_x]:
            nearby = np.argwhere(curve_mask[max(0, seed_y - 5):seed_y + 6,
                                            max(0, seed_x - 5):seed_x + 6])
            if not len(nearby): return []
            seed_x += int(nearby[0, 1]) - min(5, seed_x)
            seed_y += int(nearby[0, 0]) - min(5, seed_y)
        traced = [(seed_x, float(seed_y))]
        for direction in (-1, 1):
            y = float(seed_y); gap = 0; branch = []
            for x in range(seed_x + direction, curve_mask.shape[1] if direction > 0 else -1, direction):
                rows = np.flatnonzero(curve_mask[:, x])
                if len(rows):
                    closest = int(rows[np.argmin(abs(rows - y))])
                    if abs(closest - y) <= max(18, min(26, gap * 1.5 + 9)):
                        if gap:
                            previous_x, previous_y = branch[-1] if branch else traced[0]
                            for missing_x in range(previous_x + direction, x, direction):
                                fraction = abs(missing_x - previous_x) / abs(x - previous_x)
                                branch.append((missing_x, previous_y + fraction * (closest - previous_y)))
                        y = float(closest); gap = 0; branch.append((x, y)); continue
                gap += 1
                if gap > 45: break
            traced.extend(branch)
        traced.sort()
        if len(traced) < 8 or traced[-1][0] - traced[0][0] < 20:
            return []
        result = []
        step = max(2, curve_step)
        for x, y in traced[::step]: result.append((float(left + x), float(top + y)))
        return result
    raise ValueError("Unsupported plot mode.")


def write_csv(path: str | Path, points: list[tuple[float, float]],
              roi: tuple[int, int, int, int], limits: tuple[float, float, float, float],
              x_log: bool = False, y_log: bool = False,
              calibration: dict[str, float] | None = None) -> None:
    with Path(path).open("w", newline="", encoding="utf-8-sig") as output:
        writer = csv.writer(output)
        writer.writerow(("x", "y"))
        for point in sorted(points):
            writer.writerow(tuple(f"{value:.12g}" for value in pixel_to_value(point, roi, limits, x_log, y_log, calibration)))
