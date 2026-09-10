from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np


class InpaintEngine:
    """UI-independent LaMa ONNX inference backend."""

    _lama_net = None
    _custom_model_path: Path | None = None

    @classmethod
    def _model_path(cls) -> Path:
        if cls._custom_model_path is not None:
            return cls._custom_model_path
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
        return base / "models" / "inpainting_lama_2025jan.onnx"

    @classmethod
    def set_model_path(cls, path: str | None) -> None:
        resolved = Path(path) if path else None
        if resolved != cls._custom_model_path:
            cls._custom_model_path = resolved
            cls._lama_net = None

    @classmethod
    def _get_lama_net(cls):
        if cls._lama_net is None:
            path = cls._model_path()
            if not path.exists():
                raise FileNotFoundError(f"缺少 AI 模型文件：{path}")
            cls._lama_net = cv2.dnn.readNetFromONNX(str(path))
            cls._lama_net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            cls._lama_net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        return cls._lama_net

    @classmethod
    def inpaint(cls, rgb: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Run LaMa on a context-rich crop while preserving full resolution."""
        points = cv2.findNonZero(mask)
        if points is None:
            return rgb.copy()
        x, y, width, height = cv2.boundingRect(points)
        context = max(96, width, height)
        left = max(0, x - context)
        top = max(0, y - context)
        right = min(rgb.shape[1], x + width + context)
        bottom = min(rgb.shape[0], y + height + context)
        crop = rgb[top:bottom, left:right]
        crop_mask = mask[top:bottom, left:right]

        crop_h, crop_w = crop.shape[:2]
        side = max(crop_h, crop_w)
        pad_top = (side - crop_h) // 2
        pad_bottom = side - crop_h - pad_top
        pad_left = (side - crop_w) // 2
        pad_right = side - crop_w - pad_left
        square = cv2.copyMakeBorder(
            crop, pad_top, pad_bottom, pad_left, pad_right, cv2.BORDER_REFLECT_101
        )
        square_mask = cv2.copyMakeBorder(
            crop_mask, pad_top, pad_bottom, pad_left, pad_right,
            cv2.BORDER_CONSTANT, value=0,
        )

        image_blob = cv2.dnn.blobFromImage(
            square, 1.0 / 255.0, (512, 512), (0, 0, 0), swapRB=False, crop=False
        )
        mask_blob = cv2.dnn.blobFromImage(
            square_mask, 1.0, (512, 512), (0,), swapRB=False, crop=False
        )
        mask_blob = (mask_blob > 0).astype(np.float32)
        net = cls._get_lama_net()
        net.setInput(image_blob, "image")
        net.setInput(mask_blob, "mask")
        output = net.forward()[0].transpose(1, 2, 0)
        output = np.clip(output, 0, 255).astype(np.uint8)
        output = cv2.resize(output, (side, side), interpolation=cv2.INTER_CUBIC)
        output = output[pad_top:pad_top + crop_h, pad_left:pad_left + crop_w]

        result = rgb.copy()
        crop_result = result[top:bottom, left:right]
        selected = crop_mask > 0
        crop_result[selected] = output[selected]
        return result

