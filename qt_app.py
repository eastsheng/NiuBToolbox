from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw
from PySide6.QtCore import QEvent, QPoint, QRect, QRectF, QSize, QThread, Qt, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QIcon, QImage, QIntValidator, QMouseEvent, QPainter, QPainterPath, QPalette, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication, QColorDialog, QComboBox, QDialog, QFileDialog, QFrame, QGraphicsDropShadowEffect,
    QHBoxLayout, QLabel, QMainWindow, QMessageBox, QProgressBar, QPushButton, QSlider,
    QStackedWidget, QVBoxLayout, QWidget
)

from tools.inpaint_engine import InpaintEngine
from tools.image_compressor import ImageCompressor
from tools.image_enhancer import ImageEnhancer
from tools.id_photo_generator import IdPhotoGenerator
from tools.caj_to_pdf import CajToPdfConverter
from tools.media_converter import MediaConverter
from tools.pdf_to_markdown import PdfToMarkdownConverter


PALETTES = {
    "light": {"window": "#f4f4f6", "card": "#ffffff", "side": "#fafafa", "text": "#252525", "muted": "#898989", "line": "#e6e6e8", "canvas": "#ededf0", "hover": "#f0f0f2", "red": "#ec4141"},
    "dark": {"window": "#171719", "card": "#242426", "side": "#202022", "text": "#f2f2f2", "muted": "#99999f", "line": "#343438", "canvas": "#151517", "hover": "#303034", "red": "#ec4141"},
}

APP_VERSION = "1.0.7"
COPYRIGHT_YEAR = "2026"
COPYRIGHT_OWNER = "eastsheng"


def resource_path(relative: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative


def staged_output_dir() -> Path:
    """Create a private temporary directory for an unsaved generated result."""
    return Path(tempfile.mkdtemp(prefix="niub-result-"))


def discard_staged_output(path: str | None) -> None:
    if not path:
        return
    result = Path(path)
    parent = result.parent
    if parent.name.startswith("niub-result-"):
        shutil.rmtree(parent, ignore_errors=True)


def save_staged_file(parent: QWidget, staged: str, title: str, suggested: str, file_filter: str) -> str | None:
    destination, _ = QFileDialog.getSaveFileName(parent, title, suggested, file_filter)
    if not destination:
        return None
    shutil.copy2(staged, destination)
    return destination

TEXT = {
    "zh": {
        "app": "NiuB工具箱", "my_tools": "我的工具", "image_processing": "图片处理", "file_processing": "文件处理", "watermark": "AI 去水印",
        "local_private": "●  本地处理 · 图片不会上传", "settings": "⚙   设置",
        "local_process": "图片全程在本地处理", "delete_image": "删除图片", "choose_image": "选择图片",
        "canvas_hint": "选择图片后，用画笔涂抹需要移除的区域", "brush_size": "画笔大小",
        "repair_mode": "修复方式", "ai_mode": "AI 深度修复（推荐）", "fast_mode": "快速修复",
        "choose_prompt": "请选择一张图片", "undo": "撤销", "clear": "清除选区",
        "export": "导出图片", "start_repair": "✦  开始修复", "settings_title": "设置",
        "about": "关于", "version_info": "版本 {version}",
        "copyright_info": "版权所有 © {year} {owner}。保留所有权利。",
        "language": "界面语言", "ai_model": "AI 模型", "current_model": "当前模型", "watermark_model": "去水印模型",
        "builtin_model": "默认 LaMa 模型", "add_model": "＋ 添加本地模型", "reset_model": "使用默认模型",
        "model_hint": "支持 LaMa 接口兼容的 ONNX 模型，输入名需为 image 和 mask。",
        "add_model_title": "添加本地 AI 模型", "onnx_filter": "ONNX 模型 (*.onnx)",
        "image_filter": "常见图片 (*.jpg *.jpeg *.jpe *.jfif *.png *.webp *.bmp *.dib *.gif *.tif *.tiff *.ico *.heic *.heif *.avif *.tga *.ppm *.pgm *.pbm);;所有文件 (*.*)", "open_failed": "打开失败",
        "repairing": "正在后台进行 AI 修复…", "repair_done": "修复完成，不满意可撤销",
        "repair_failed": "修复失败", "wait_close": "AI 修复仍在进行，请完成后再关闭",
        "model_missing_title": "缺少 AI 模型",
        "model_missing": "请先下载 inpainting_lama_2025jan.onnx，并保存到：\n{path}\n\n也可以在当前页面选择其他兼容的去水印模型。",
        "export_title": "导出图片", "export_name": "修复后的图片.png", "png_filter": "PNG 图片 (*.png)",
        "saved": "已保存：{name}",
        "pdf_tool": "PDF 转 Markdown", "pdf_title": "PDF 转 Markdown",
        "pdf_subtitle": "提取 PDF 正文与图片，并在 Markdown 中按原文位置显示",
        "choose_pdf": "选择 PDF", "no_pdf": "请选择一个 PDF 文件",
        "convert_pdf": "开始转换", "open_output": "打开输出文件夹", "save_result": "保存结果",
        "save_result_title": "保存生成结果", "choose_save_folder": "选择保存位置", "result_ready": "生成完成，请点击“保存结果”",
        "pdf_filter": "PDF 文件 (*.pdf)", "pdf_failed": "PDF 转换失败",
        "pdf_done": "转换完成：{name}", "extracting_text": "正在提取 PDF 正文…",
        "extracting_images": "正在提取并定位 PDF 图片…", "rendering_pages": "正在处理 PDF 内容…",
        "saving": "正在保存 Markdown…", "done": "转换完成",
        "wait_close_pdf": "PDF 仍在转换，请完成后再关闭",
        "media_tool": "视频与 GIF 转换", "media_title": "视频与 GIF 相互转换",
        "media_subtitle": "支持常见视频转 GIF，以及 GIF 转 MP4",
        "choose_media": "选择文件", "no_media": "请选择视频或 GIF 文件",
        "media_filter": "视频与 GIF (*.mp4 *.mov *.avi *.mkv *.webm *.m4v *.wmv *.gif)",
        "media_fps": "帧率", "media_size": "输出宽度", "original_fps": "原始帧率", "original_size": "原始尺寸",
        "start_convert": "开始转换", "media_converting": "正在后台转换…",
        "media_done": "转换完成：{name}", "media_failed": "媒体转换失败",
        "video_to_gif": "视频 → GIF", "gif_to_video": "GIF → MP4",
        "wait_close_media": "媒体仍在转换，请完成后再关闭",
        "compress_tool": "图片压缩", "compress_title": "图片压缩",
        "compress_subtitle": "保持原始尺寸，以高画质减小图片文件大小",
        "choose_compress_image": "选择图片", "no_compress_image": "请选择需要压缩的图片",
        "compress_format": "输出格式", "format_original": "保持原格式（推荐）", "compress_quality": "压缩质量 (%)",
        "quality_hint": "可选择或输入 1–100，数值越低文件越小",
        "start_compress": "开始压缩", "compressing": "正在后台压缩…",
        "compress_done": "压缩完成：{before} → {after} · 减少 {saved}% · 请点击“保存结果”",
        "compress_failed": "图片压缩失败", "wait_close_compress": "图片仍在压缩，请完成后再关闭",
        "enhance_tool": "图片变清晰", "enhance_title": "模糊图片变清晰",
        "enhance_subtitle": "使用本地 Real-ESRGAN AI 重建纹理与边缘，不上传图片",
        "choose_enhance_image": "选择图片", "no_enhance_image": "请选择需要增强清晰度的图片",
        "enhance_style": "图片类型", "style_photo": "照片", "style_art": "动漫 / 插画",
        "enhance_noise": "降噪", "noise_none": "无", "noise_low": "低", "noise_medium": "中", "noise_high": "高",
        "enhance_scale": "放大倍率", "scale_2x": "放大 2 倍", "scale_4x": "放大 4 倍",
        "enhance_engine": "AI 模型", "choose_enhance_engine": "选择本地模型", "download_enhance_engine": "下载模型",
        "enhance_engine_ready": "已就绪：{name}", "enhance_engine_missing": "未找到 Real-ESRGAN AI 引擎",
        "enhance_engine_filter": "Real-ESRGAN 模型或引擎 (*.onnx *.exe)",
        "enhance_hint": "推荐 ONNX 模型：无需独立显卡，可使用 CPU；模型下载后保存在 models 文件夹中",
        "start_enhance": "开始增强", "enhancing": "正在后台增强图片清晰度…",
        "enhance_done": "增强完成：{before} → {after} · 请点击“保存结果”",
        "enhance_failed": "图片增强失败", "wait_close_enhance": "图片仍在增强，请完成后再关闭",
        "id_photo_tool": "证件照生成", "id_photo_title": "证件照生成",
        "id_photo_subtitle": "使用本地 AI 抠出人像，并替换为纯色或渐变背景",
        "choose_id_photo": "选择人像照片", "no_id_photo": "请选择一张正面人像照片",
        "id_photo_size": "证件照尺寸", "one_inch": "一寸（295 × 413 px）", "two_inch": "二寸（413 × 579 px）",
        "id_background": "背景样式", "background_blue": "蓝底", "background_red": "红底",
        "background_white": "白底", "background_gradient": "渐变底", "background_custom": "自定义纯色",
        "primary_color": "主颜色", "secondary_color": "渐变颜色", "choose_color": "选择颜色",
        "id_model": "人像模型", "choose_id_model": "选择本地模型", "download_id_model": "下载模型",
        "id_model_ready": "已就绪：{name}", "id_model_missing": "未找到 MODNet 人像抠图模型",
        "id_model_filter": "MODNet 模型 (*.onnx)", "id_model_hint": "模型下载后保存在 models 文件夹中",
        "generate_id_photo": "生成证件照", "generating_id_photo": "正在后台抠取人像并生成证件照…",
        "id_photo_done": "证件照已生成：{name}", "id_photo_failed": "证件照生成失败",
        "wait_close_id_photo": "证件照仍在生成，请完成后再关闭",
        "caj_tool": "CAJ 转 PDF", "caj_title": "CAJ 转 PDF",
        "caj_subtitle": "在本地将 CAJ、NH 或 KDH 文献文件转换为 PDF",
        "choose_caj": "选择 CAJ 文件", "no_caj": "请选择需要转换的 CAJ 文件",
        "caj_filter": "CAJ 文件 (*.caj *.nh *.kdh)", "convert_caj": "开始转换",
        "caj_converting": "正在后台转换…", "caj_done": "转换完成：{name}",
        "caj_failed": "CAJ 转换失败", "wait_close_caj": "CAJ 仍在转换，请完成后再关闭",
    },
    "en": {
        "app": "NiuB Toolbox", "my_tools": "My Tools", "image_processing": "Image Processing", "file_processing": "File Processing", "watermark": "AI Watermark Remover",
        "local_private": "●  Local processing · Nothing is uploaded", "settings": "⚙   Settings",
        "local_process": "Images are processed entirely on this device", "delete_image": "Remove Image", "choose_image": "Choose Image",
        "canvas_hint": "Choose an image, then paint over the area to remove", "brush_size": "Brush Size",
        "repair_mode": "Repair Mode", "ai_mode": "AI Deep Repair (Recommended)", "fast_mode": "Quick Repair",
        "choose_prompt": "Choose an image", "undo": "Undo", "clear": "Clear Selection",
        "export": "Export", "start_repair": "✦  Start Repair", "settings_title": "Settings",
        "about": "About", "version_info": "Version {version}",
        "copyright_info": "Copyright © {year} {owner}. All rights reserved.",
        "language": "Language", "ai_model": "AI Model", "current_model": "Current Model", "watermark_model": "Watermark Model",
        "builtin_model": "Default LaMa model", "add_model": "＋ Add Local Model", "reset_model": "Use Default Model",
        "model_hint": "Supports LaMa-compatible ONNX models with image and mask inputs.",
        "add_model_title": "Add Local AI Model", "onnx_filter": "ONNX Model (*.onnx)",
        "image_filter": "Common Images (*.jpg *.jpeg *.jpe *.jfif *.png *.webp *.bmp *.dib *.gif *.tif *.tiff *.ico *.heic *.heif *.avif *.tga *.ppm *.pgm *.pbm);;All Files (*.*)", "open_failed": "Open Failed",
        "repairing": "Running AI repair in the background…", "repair_done": "Repair complete — you can undo it",
        "repair_failed": "Repair Failed", "wait_close": "AI repair is still running. Please wait before closing.",
        "model_missing_title": "AI Model Missing",
        "model_missing": "Download inpainting_lama_2025jan.onnx and save it to:\n{path}\n\nYou can also select another compatible watermark model on this page.",
        "export_title": "Export Image", "export_name": "repaired-image.png", "png_filter": "PNG Image (*.png)",
        "saved": "Saved: {name}",
        "pdf_tool": "PDF to Markdown", "pdf_title": "PDF to Markdown",
        "pdf_subtitle": "Extract PDF text and place images at their corresponding Markdown positions",
        "choose_pdf": "Choose PDF", "no_pdf": "Choose a PDF file",
        "convert_pdf": "Convert", "open_output": "Open Output Folder", "save_result": "Save Result",
        "save_result_title": "Save Generated Result", "choose_save_folder": "Choose Save Location", "result_ready": "Generated. Click “Save Result” to save it.",
        "pdf_filter": "PDF Files (*.pdf)", "pdf_failed": "PDF Conversion Failed",
        "pdf_done": "Conversion complete: {name}", "extracting_text": "Extracting PDF text…",
        "extracting_images": "Extracting and positioning PDF images…", "rendering_pages": "Processing PDF content…",
        "saving": "Saving Markdown…", "done": "Conversion complete",
        "wait_close_pdf": "PDF conversion is still running. Please wait before closing.",
        "media_tool": "Video and GIF Converter", "media_title": "Video and GIF Converter",
        "media_subtitle": "Convert common video formats to GIF, or GIF to MP4",
        "choose_media": "Choose File", "no_media": "Choose a video or GIF file",
        "media_filter": "Video and GIF (*.mp4 *.mov *.avi *.mkv *.webm *.m4v *.wmv *.gif)",
        "media_fps": "Frame Rate", "media_size": "Output Width", "original_fps": "Original Frame Rate", "original_size": "Original Size",
        "start_convert": "Convert", "media_converting": "Converting in the background…",
        "media_done": "Conversion complete: {name}", "media_failed": "Media Conversion Failed",
        "video_to_gif": "Video → GIF", "gif_to_video": "GIF → MP4",
        "wait_close_media": "Media conversion is still running. Please wait before closing.",
        "compress_tool": "Image Compressor", "compress_title": "Image Compressor",
        "compress_subtitle": "Reduce file size at high visual quality without changing dimensions",
        "choose_compress_image": "Choose Image", "no_compress_image": "Choose an image to compress",
        "compress_format": "Output Format", "format_original": "Keep Original (Recommended)", "compress_quality": "Compression Quality (%)",
        "quality_hint": "Choose or enter 1–100; lower values create smaller files",
        "start_compress": "Compress", "compressing": "Compressing in the background…",
        "compress_done": "Done: {before} → {after} · {saved}% smaller · Click “Save Result”",
        "compress_failed": "Image Compression Failed", "wait_close_compress": "Image compression is still running. Please wait before closing.",
        "enhance_tool": "Image Clarity", "enhance_title": "Make Blurry Images Clearer",
        "enhance_subtitle": "Reconstruct texture and edges with local Real-ESRGAN AI; images are never uploaded",
        "choose_enhance_image": "Choose Image", "no_enhance_image": "Choose an image to enhance",
        "enhance_style": "Image Type", "style_photo": "Photo", "style_art": "Anime / Artwork",
        "enhance_noise": "Noise Reduction", "noise_none": "None", "noise_low": "Low", "noise_medium": "Medium", "noise_high": "High",
        "enhance_scale": "Upscaling", "scale_2x": "Upscale 2×", "scale_4x": "Upscale 4×",
        "enhance_engine": "AI Model", "choose_enhance_engine": "Choose Local Model", "download_enhance_engine": "Download Model",
        "enhance_engine_ready": "Ready: {name}", "enhance_engine_missing": "Real-ESRGAN AI engine not found",
        "enhance_engine_filter": "Real-ESRGAN Model or Engine (*.onnx *.exe)",
        "enhance_hint": "ONNX is recommended and works on CPU without a discrete GPU; save downloaded models in the models folder",
        "start_enhance": "Enhance", "enhancing": "Enhancing image clarity in the background…",
        "enhance_done": "Done: {before} → {after} · Click “Save Result”",
        "enhance_failed": "Image Enhancement Failed", "wait_close_enhance": "Image enhancement is still running. Please wait before closing.",
        "id_photo_tool": "ID Photo", "id_photo_title": "ID Photo Generator",
        "id_photo_subtitle": "Extract portraits with local AI and apply a solid or gradient background",
        "choose_id_photo": "Choose Portrait", "no_id_photo": "Choose a front-facing portrait photo",
        "id_photo_size": "Photo Size", "one_inch": "1-inch (295 × 413 px)", "two_inch": "2-inch (413 × 579 px)",
        "id_background": "Background", "background_blue": "Blue", "background_red": "Red",
        "background_white": "White", "background_gradient": "Gradient", "background_custom": "Custom Solid",
        "primary_color": "Primary", "secondary_color": "Gradient Color", "choose_color": "Choose Color",
        "id_model": "Portrait Model", "choose_id_model": "Choose Local Model", "download_id_model": "Download Model",
        "id_model_ready": "Ready: {name}", "id_model_missing": "MODNet portrait model not found",
        "id_model_filter": "MODNet Model (*.onnx)", "id_model_hint": "Save the downloaded model in the models folder",
        "generate_id_photo": "Generate ID Photo", "generating_id_photo": "Extracting portrait and creating ID photo in the background…",
        "id_photo_done": "ID photo created: {name}", "id_photo_failed": "ID Photo Generation Failed",
        "wait_close_id_photo": "The ID photo is still being generated. Please wait before closing.",
        "caj_tool": "CAJ to PDF", "caj_title": "CAJ to PDF",
        "caj_subtitle": "Convert CAJ, NH, or KDH document files to PDF locally",
        "choose_caj": "Choose CAJ File", "no_caj": "Choose a CAJ file to convert",
        "caj_filter": "CAJ Files (*.caj *.nh *.kdh)", "convert_caj": "Convert",
        "caj_converting": "Converting in the background…", "caj_done": "Conversion complete: {name}",
        "caj_failed": "CAJ Conversion Failed", "wait_close_caj": "CAJ conversion is still running. Please wait before closing.",
    },
}


def pil_to_pixmap(image: Image.Image) -> QPixmap:
    rgba = image.convert("RGBA")
    data = rgba.tobytes("raw", "RGBA")
    qimage = QImage(data, rgba.width, rgba.height, QImage.Format_RGBA8888).copy()
    return QPixmap.fromImage(qimage)


def symbol_icon(symbol: str, color: str) -> QIcon:
    """Render sidebar symbols into an equal-size icon slot for exact text alignment."""
    pixmap = QPixmap(18, 18)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setPen(QColor(color))
    font = painter.font(); font.setFamily("Segoe UI Symbol"); font.setPointSize(9); font.setBold(True)
    painter.setFont(font); painter.drawText(pixmap.rect(), Qt.AlignCenter, symbol); painter.end()
    return QIcon(pixmap)


def window_control_icon(kind: str, color: str) -> QIcon:
    """Draw consistent title-bar controls instead of relying on mismatched font glyphs."""
    def draw(icon_color: str) -> QPixmap:
        pixmap = QPixmap(18, 18); pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap); painter.setRenderHint(QPainter.Antialiasing, True)
        pen = QPen(QColor(icon_color), 1.6); pen.setCapStyle(Qt.RoundCap); pen.setJoinStyle(Qt.RoundJoin); painter.setPen(pen)
        if kind == "minimize":
            painter.drawLine(4, 12, 14, 12)
        elif kind == "maximize":
            painter.drawRoundedRect(QRectF(4, 4, 10, 10), 1, 1)
        elif kind == "close":
            painter.drawLine(5, 5, 13, 13); painter.drawLine(13, 5, 5, 13)
        elif kind == "sun":
            painter.drawEllipse(QRectF(6, 6, 6, 6))
            for start, end in (((9, 2), (9, 4)), ((9, 14), (9, 16)), ((2, 9), (4, 9)), ((14, 9), (16, 9)),
                               ((4, 4), (5.4, 5.4)), ((12.6, 12.6), (14, 14)), ((14, 4), (12.6, 5.4)), ((5.4, 12.6), (4, 14))):
                painter.drawLine(*start, *end)
        else:  # moon
            outer = QPainterPath(); outer.addEllipse(QRectF(3, 2, 12, 14))
            cutout = QPainterPath(); cutout.addEllipse(QRectF(7, 0, 11, 12))
            painter.fillPath(outer.subtracted(cutout), QColor(icon_color))
        painter.end(); return pixmap

    icon = QIcon(); icon.addPixmap(draw(color), QIcon.Normal); icon.addPixmap(draw("#ffffff"), QIcon.Active)
    return icon


class RepairWorker(QThread):
    """Run OpenCV/ONNX inference away from Qt's GUI thread."""

    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, rgba: np.ndarray, mask: np.ndarray, use_ai: bool, parent=None) -> None:
        super().__init__(parent)
        self.rgba = rgba
        self.mask = mask
        self.use_ai = use_ai

    def run(self) -> None:
        try:
            rgb = self.rgba[:, :, :3]
            if self.use_ai:
                repaired = InpaintEngine.inpaint(rgb, self.mask)
            else:
                bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
                repaired = cv2.cvtColor(
                    cv2.inpaint(bgr, self.mask, 3, cv2.INPAINT_TELEA),
                    cv2.COLOR_BGR2RGB,
                )
            result = self.rgba.copy()
            selected = self.mask > 0
            result[selected, :3] = repaired[selected]
            self.succeeded.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class PdfConvertWorker(QThread):
    progress = Signal(str, int)
    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, pdf_path: str, language: str, parent=None) -> None:
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.language = language

    def run(self) -> None:
        stage = staged_output_dir()
        try:
            converter = PdfToMarkdownConverter(self.language)
            output = converter.convert(
                self.pdf_path,
                lambda key, percent: self.progress.emit(key, percent),
                stage,
            )
            self.succeeded.emit(str(output))
        except Exception as exc:
            shutil.rmtree(stage, ignore_errors=True)
            self.failed.emit(str(exc))


class PdfToMarkdownPanel(QWidget):
    def __init__(self, window) -> None:
        super().__init__()
        self.window = window
        self.pdf_path: str | None = None
        self.output_path: str | None = None
        self.worker: PdfConvertWorker | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 17, 22, 20)
        layout.setSpacing(12)
        self.title = QLabel(); self.title.setObjectName("pageTitle"); layout.addWidget(self.title)
        self.subtitle = QLabel(); self.subtitle.setObjectName("muted"); self.subtitle.setWordWrap(True); layout.addWidget(self.subtitle)

        card = QFrame(); card.setObjectName("toolbar")
        card_layout = QVBoxLayout(card); card_layout.setContentsMargins(22, 22, 22, 22); card_layout.setSpacing(14)
        self.file_label = QLabel(); self.file_label.setAlignment(Qt.AlignCenter); self.file_label.setWordWrap(True)
        card_layout.addStretch(); card_layout.addWidget(self.file_label)
        row = QHBoxLayout(); row.addStretch()
        self.choose_btn = QPushButton(); self.choose_btn.setObjectName("primary"); self.choose_btn.clicked.connect(self.choose_pdf); row.addWidget(self.choose_btn)
        self.convert_btn = QPushButton(); self.convert_btn.clicked.connect(self.convert_pdf); row.addWidget(self.convert_btn)
        self.open_btn = QPushButton(); self.open_btn.clicked.connect(self.save_output); row.addWidget(self.open_btn)
        row.addStretch(); card_layout.addLayout(row)
        self.progress = QProgressBar(); self.progress.setRange(0, 100); self.progress.setValue(0); self.progress.setTextVisible(False); card_layout.addWidget(self.progress)
        self.status = QLabel(); self.status.setObjectName("muted"); self.status.setAlignment(Qt.AlignCenter); card_layout.addWidget(self.status)
        card_layout.addStretch(); layout.addWidget(card, 1)
        self.retranslate(); self.update_actions()

    def retranslate(self) -> None:
        t = self.window.tr
        self.title.setText(t("pdf_title")); self.subtitle.setText(t("pdf_subtitle"))
        self.choose_btn.setText(t("choose_pdf")); self.convert_btn.setText(t("convert_pdf")); self.open_btn.setText(t("save_result"))
        if self.pdf_path is None:
            self.file_label.setText(t("no_pdf"))
        if self.worker is None and self.output_path is None:
            self.status.setText("")

    def update_actions(self) -> None:
        busy = self.worker is not None
        self.choose_btn.setEnabled(not busy)
        self.convert_btn.setEnabled(self.pdf_path is not None and not busy)
        self.open_btn.setEnabled(self.output_path is not None and not busy)

    def choose_pdf(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, self.window.tr("choose_pdf"), "", self.window.tr("pdf_filter"))
        if not path:
            return
        discard_staged_output(self.output_path); self.pdf_path = path; self.output_path = None; self.progress.setValue(0)
        self.file_label.setText(f"{Path(path).name}\n{path}"); self.status.setText(""); self.update_actions()

    def convert_pdf(self) -> None:
        if self.worker is not None or self.pdf_path is None:
            return
        discard_staged_output(self.output_path); self.output_path = None; self.progress.setValue(0)
        self.worker = PdfConvertWorker(self.pdf_path, self.window.language, self)
        self.worker.progress.connect(self.on_progress); self.worker.succeeded.connect(self.on_succeeded)
        self.worker.failed.connect(self.on_failed); self.worker.finished.connect(self.on_finished)
        self.worker.start(); self.update_actions()

    def on_progress(self, key: str, percent: int) -> None:
        self.progress.setValue(percent)
        if key in TEXT[self.window.language]:
            self.status.setText(self.window.tr(key))

    def on_succeeded(self, output_path: str) -> None:
        self.output_path = output_path; self.progress.setValue(100)
        self.status.setText(self.window.tr("result_ready"))

    def on_failed(self, message: str) -> None:
        self.progress.setValue(0); self.status.setText(self.window.tr("pdf_failed"))
        QMessageBox.critical(self, self.window.tr("pdf_failed"), message)

    def on_finished(self) -> None:
        worker = self.worker; self.worker = None
        if worker is not None:
            worker.deleteLater()
        self.update_actions()

    def save_output(self) -> None:
        if not self.output_path or not self.pdf_path: return
        folder = QFileDialog.getExistingDirectory(self, self.window.tr("choose_save_folder"), str(Path(self.pdf_path).parent))
        if not folder: return
        source = Path(self.output_path); destination = Path(folder) / source.name; index = 2
        while destination.exists():
            destination = Path(folder) / f"{source.name}_{index}"; index += 1
        shutil.copytree(source, destination)
        discard_staged_output(self.output_path); self.output_path = None
        self.status.setText(self.window.tr("saved").format(name=destination.name)); self.update_actions()


class MediaConvertWorker(QThread):
    progress = Signal(int)
    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, source_path: str, fps: int, max_width: int, parent=None) -> None:
        super().__init__(parent)
        self.source_path = source_path
        self.fps = fps
        self.max_width = max_width

    def run(self) -> None:
        stage = staged_output_dir()
        try:
            output = MediaConverter().convert(
                self.source_path,
                self.fps,
                self.max_width,
                self.progress.emit,
                stage,
            )
            self.succeeded.emit(str(output))
        except Exception as exc:
            shutil.rmtree(stage, ignore_errors=True)
            self.failed.emit(str(exc))


class MediaConverterPanel(QWidget):
    def __init__(self, window) -> None:
        super().__init__()
        self.window = window
        self.source_path: str | None = None
        self.output_path: str | None = None
        self.worker: MediaConvertWorker | None = None

        layout = QVBoxLayout(self); layout.setContentsMargins(22, 17, 22, 20); layout.setSpacing(12)
        self.title = QLabel(); self.title.setObjectName("pageTitle"); layout.addWidget(self.title)
        self.subtitle = QLabel(); self.subtitle.setObjectName("muted"); layout.addWidget(self.subtitle)
        card = QFrame(); card.setObjectName("toolbar")
        card_layout = QVBoxLayout(card); card_layout.setContentsMargins(22, 22, 22, 22); card_layout.setSpacing(14)
        card_layout.addStretch()
        self.file_label = QLabel(); self.file_label.setAlignment(Qt.AlignCenter); self.file_label.setWordWrap(True); card_layout.addWidget(self.file_label)
        self.direction_label = QLabel(); self.direction_label.setObjectName("muted"); self.direction_label.setAlignment(Qt.AlignCenter); card_layout.addWidget(self.direction_label)
        options = QHBoxLayout(); options.addStretch()
        self.fps_label = QLabel(); options.addWidget(self.fps_label)
        self.fps_combo = QComboBox(); self.fps_combo.setObjectName("repairMode")
        self.fps_combo.addItem("", 0)
        for value in (8, 12, 15, 20, 24): self.fps_combo.addItem(f"{value} FPS", value)
        self.fps_combo.setCurrentIndex(0); options.addWidget(self.fps_combo)
        options.addSpacing(12); self.size_label = QLabel(); options.addWidget(self.size_label)
        self.size_combo = QComboBox(); self.size_combo.setObjectName("repairMode"); options.addWidget(self.size_combo)
        options.addStretch(); card_layout.addLayout(options)
        buttons = QHBoxLayout(); buttons.addStretch()
        self.choose_btn = QPushButton(); self.choose_btn.setObjectName("primary"); self.choose_btn.clicked.connect(self.choose_media); buttons.addWidget(self.choose_btn)
        self.convert_btn = QPushButton(); self.convert_btn.clicked.connect(self.convert_media); buttons.addWidget(self.convert_btn)
        self.open_btn = QPushButton(); self.open_btn.clicked.connect(self.save_output); buttons.addWidget(self.open_btn)
        buttons.addStretch(); card_layout.addLayout(buttons)
        self.progress = QProgressBar(); self.progress.setRange(0, 100); self.progress.setTextVisible(False); card_layout.addWidget(self.progress)
        self.status = QLabel(); self.status.setObjectName("muted"); self.status.setAlignment(Qt.AlignCenter); card_layout.addWidget(self.status)
        card_layout.addStretch(); layout.addWidget(card, 1)
        self.retranslate(); self.update_actions()

    def retranslate(self) -> None:
        t = self.window.tr
        self.title.setText(t("media_title")); self.subtitle.setText(t("media_subtitle"))
        self.fps_label.setText(t("media_fps")); self.size_label.setText(t("media_size"))
        self.fps_combo.setItemText(0, t("original_fps"))
        selected_width = self.size_combo.currentData()
        self.size_combo.clear()
        self.size_combo.addItem(t("original_size"), 0)
        self.size_combo.addItem("480 px", 480); self.size_combo.addItem("720 px", 720); self.size_combo.addItem("1080 px", 1080)
        index = self.size_combo.findData(selected_width if selected_width is not None else 0)
        self.size_combo.setCurrentIndex(max(0, index))
        self.choose_btn.setText(t("choose_media")); self.convert_btn.setText(t("start_convert")); self.open_btn.setText(t("save_result"))
        if self.source_path is None: self.file_label.setText(t("no_media"))
        self.update_direction()

    def update_direction(self) -> None:
        if self.source_path is None:
            self.direction_label.setText("")
        else:
            self.direction_label.setText(self.window.tr("gif_to_video" if Path(self.source_path).suffix.lower() == ".gif" else "video_to_gif"))

    def update_actions(self) -> None:
        busy = self.worker is not None
        self.choose_btn.setEnabled(not busy); self.fps_combo.setEnabled(not busy); self.size_combo.setEnabled(not busy)
        self.convert_btn.setEnabled(self.source_path is not None and not busy)
        self.open_btn.setEnabled(self.output_path is not None and not busy)

    def choose_media(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, self.window.tr("choose_media"), "", self.window.tr("media_filter"))
        if not path: return
        discard_staged_output(self.output_path); self.source_path = path; self.output_path = None; self.progress.setValue(0); self.status.setText("")
        self.file_label.setText(f"{Path(path).name}\n{path}"); self.update_direction(); self.update_actions()

    def convert_media(self) -> None:
        if self.worker is not None or self.source_path is None: return
        discard_staged_output(self.output_path); self.output_path = None; self.progress.setValue(0); self.status.setText(self.window.tr("media_converting"))
        self.worker = MediaConvertWorker(self.source_path, int(self.fps_combo.currentData()), int(self.size_combo.currentData()), self)
        self.worker.progress.connect(self.progress.setValue); self.worker.succeeded.connect(self.on_succeeded)
        self.worker.failed.connect(self.on_failed); self.worker.finished.connect(self.on_finished)
        self.worker.start(); self.update_actions()

    def on_succeeded(self, output_path: str) -> None:
        self.output_path = output_path; self.progress.setValue(100)
        self.status.setText(self.window.tr("result_ready"))

    def on_failed(self, message: str) -> None:
        self.progress.setValue(0); self.status.setText(self.window.tr("media_failed"))
        QMessageBox.critical(self, self.window.tr("media_failed"), message)

    def on_finished(self) -> None:
        worker = self.worker; self.worker = None
        if worker is not None: worker.deleteLater()
        self.update_actions()

    def save_output(self) -> None:
        if not self.output_path or not self.source_path: return
        staged = self.output_path; suggested = str(Path(self.source_path).with_name(Path(staged).name))
        suffix = Path(staged).suffix.lower(); file_filter = "GIF (*.gif)" if suffix == ".gif" else "MP4 (*.mp4)"
        saved = save_staged_file(self, staged, self.window.tr("save_result_title"), suggested, file_filter)
        if saved:
            discard_staged_output(staged); self.output_path = None
            self.status.setText(self.window.tr("saved").format(name=Path(saved).name)); self.update_actions()


class ImageCompressWorker(QThread):
    succeeded = Signal(str, int, int)
    failed = Signal(str)

    def __init__(self, source_path: str, output_format: str, quality: int, parent=None) -> None:
        super().__init__(parent)
        self.source_path = source_path
        self.output_format = output_format
        self.quality = quality

    def run(self) -> None:
        stage = staged_output_dir()
        try:
            output, before, after = ImageCompressor().compress(
                self.source_path, self.output_format, self.quality, stage
            )
            self.succeeded.emit(str(output), before, after)
        except Exception as exc:
            shutil.rmtree(stage, ignore_errors=True)
            self.failed.emit(str(exc))


class ImageCompressorPanel(QWidget):
    def __init__(self, window) -> None:
        super().__init__()
        self.window = window
        self.source_path: str | None = None
        self.output_path: str | None = None
        self.worker: ImageCompressWorker | None = None

        layout = QVBoxLayout(self); layout.setContentsMargins(22, 17, 22, 20); layout.setSpacing(12)
        self.title = QLabel(); self.title.setObjectName("pageTitle"); layout.addWidget(self.title)
        self.subtitle = QLabel(); self.subtitle.setObjectName("muted"); self.subtitle.setWordWrap(True); layout.addWidget(self.subtitle)
        card = QFrame(); card.setObjectName("toolbar")
        card_layout = QVBoxLayout(card); card_layout.setContentsMargins(22, 22, 22, 22); card_layout.setSpacing(16)
        card_layout.addStretch()
        self.file_label = QLabel(); self.file_label.setAlignment(Qt.AlignCenter); self.file_label.setWordWrap(True); card_layout.addWidget(self.file_label)
        options = QHBoxLayout(); options.addStretch()
        self.format_label = QLabel(); options.addWidget(self.format_label)
        self.format_combo = QComboBox(); self.format_combo.setObjectName("repairMode")
        for label, value in (("", "ORIGINAL"), ("JPEG", "JPEG"), ("PNG", "PNG"), ("WebP", "WEBP"), ("GIF", "GIF"), ("TIFF", "TIFF"), ("BMP", "BMP"), ("ICO", "ICO"), ("HEIC", "HEIF"), ("AVIF", "AVIF"), ("TGA", "TGA")):
            self.format_combo.addItem(label, value)
        options.addWidget(self.format_combo); options.addSpacing(14)
        self.quality_label = QLabel(); options.addWidget(self.quality_label)
        self.quality_combo = QComboBox(); self.quality_combo.setObjectName("repairMode")
        self.quality_combo.setEditable(True)
        self.quality_combo.lineEdit().setValidator(QIntValidator(1, 100, self.quality_combo))
        for value in (90, 85, 80, 70, 60, 50): self.quality_combo.addItem(str(value), value)
        self.quality_combo.setCurrentText("90")
        self.quality_combo.setFixedWidth(115)
        options.addWidget(self.quality_combo); options.addStretch(); card_layout.addLayout(options)
        buttons = QHBoxLayout(); buttons.addStretch()
        self.choose_btn = QPushButton(); self.choose_btn.setObjectName("primary"); self.choose_btn.clicked.connect(self.choose_image); buttons.addWidget(self.choose_btn)
        self.compress_btn = QPushButton(); self.compress_btn.clicked.connect(self.compress_image); buttons.addWidget(self.compress_btn)
        self.open_btn = QPushButton(); self.open_btn.clicked.connect(self.save_output); buttons.addWidget(self.open_btn)
        buttons.addStretch(); card_layout.addLayout(buttons)
        self.progress = QProgressBar(); self.progress.setRange(0, 100); self.progress.setTextVisible(False); card_layout.addWidget(self.progress)
        self.status = QLabel(); self.status.setObjectName("muted"); self.status.setAlignment(Qt.AlignCenter); card_layout.addWidget(self.status)
        card_layout.addStretch(); layout.addWidget(card, 1)
        self.retranslate(); self.update_actions()

    @staticmethod
    def readable_size(size: int) -> str:
        value = float(size)
        for unit in ("B", "KB", "MB", "GB"):
            if value < 1024 or unit == "GB":
                return f"{value:.0f} {unit}" if unit == "B" else f"{value:.2f} {unit}"
            value /= 1024
        return f"{size} B"

    def retranslate(self) -> None:
        t = self.window.tr
        self.title.setText(t("compress_title")); self.subtitle.setText(t("compress_subtitle"))
        self.format_label.setText(t("compress_format")); self.format_combo.setItemText(0, t("format_original"))
        self.quality_label.setText(t("compress_quality")); self.quality_combo.setToolTip(t("quality_hint"))
        self.choose_btn.setText(t("choose_compress_image")); self.compress_btn.setText(t("start_compress")); self.open_btn.setText(t("save_result"))
        if self.source_path is None: self.file_label.setText(t("no_compress_image"))

    def update_actions(self) -> None:
        busy = self.worker is not None
        self.choose_btn.setEnabled(not busy); self.format_combo.setEnabled(not busy); self.quality_combo.setEnabled(not busy)
        self.compress_btn.setEnabled(self.source_path is not None and not busy)
        self.open_btn.setEnabled(self.output_path is not None and not busy)

    def choose_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, self.window.tr("choose_compress_image"), "", self.window.tr("image_filter"))
        if not path: return
        try:
            with Image.open(path) as image:
                dimensions = f"{image.width}×{image.height}"
        except Exception as exc:
            QMessageBox.critical(self, self.window.tr("open_failed"), str(exc)); return
        discard_staged_output(self.output_path); self.source_path = path; self.output_path = None; self.progress.setValue(0); self.status.setText("")
        size = self.readable_size(Path(path).stat().st_size)
        self.file_label.setText(f"{Path(path).name}\n{dimensions} · {size}")
        self.update_actions()

    def compress_image(self) -> None:
        if self.worker is not None or self.source_path is None: return
        quality_text = self.quality_combo.currentText().strip().rstrip("%").strip()
        quality = max(1, min(100, int(quality_text or "90")))
        self.quality_combo.setCurrentText(str(quality))
        discard_staged_output(self.output_path); self.output_path = None; self.progress.setRange(0, 0); self.status.setText(self.window.tr("compressing"))
        self.worker = ImageCompressWorker(
            self.source_path, str(self.format_combo.currentData()), quality, self
        )
        self.worker.succeeded.connect(self.on_succeeded); self.worker.failed.connect(self.on_failed)
        self.worker.finished.connect(self.on_finished); self.worker.start(); self.update_actions()

    def on_succeeded(self, output_path: str, before: int, after: int) -> None:
        self.output_path = output_path
        saved = max(0, round((1 - after / before) * 100)) if before else 0
        self.status.setText(self.window.tr("compress_done").format(
            name=Path(output_path).name, before=self.readable_size(before), after=self.readable_size(after), saved=saved
        ))

    def on_failed(self, message: str) -> None:
        self.status.setText(self.window.tr("compress_failed"))
        QMessageBox.critical(self, self.window.tr("compress_failed"), message)

    def on_finished(self) -> None:
        self.progress.setRange(0, 100); self.progress.setValue(100 if self.output_path else 0)
        worker = self.worker; self.worker = None
        if worker is not None: worker.deleteLater()
        self.update_actions()

    def save_output(self) -> None:
        if not self.output_path or not self.source_path: return
        staged = self.output_path; suggested = str(Path(self.source_path).with_name(Path(staged).name))
        suffix = Path(staged).suffix; file_filter = f"{suffix.upper().lstrip('.')} (*{suffix});;All Files (*.*)"
        saved = save_staged_file(self, staged, self.window.tr("save_result_title"), suggested, file_filter)
        if saved:
            discard_staged_output(staged); self.output_path = None
            self.status.setText(self.window.tr("saved").format(name=Path(saved).name)); self.update_actions()


class ImageEnhanceWorker(QThread):
    succeeded = Signal(str, int, int, int, int)
    failed = Signal(str)

    def __init__(self, source_path: str, engine_path: str, style: str, noise: str, scale: int, parent=None) -> None:
        super().__init__(parent)
        self.source_path = source_path
        self.engine_path = engine_path
        self.style = style
        self.noise = noise
        self.scale = scale

    def run(self) -> None:
        stage = staged_output_dir()
        try:
            output, before, after = ImageEnhancer().enhance(self.source_path, self.engine_path, self.style, self.noise, self.scale, stage)
            self.succeeded.emit(str(output), before[0], before[1], after[0], after[1])
        except Exception as exc:
            shutil.rmtree(stage, ignore_errors=True)
            self.failed.emit(str(exc))


class ImageEnhancerPanel(QWidget):
    def __init__(self, window) -> None:
        super().__init__()
        self.window = window
        self.source_path: str | None = None
        self.output_path: str | None = None
        self.engine_path = str(window.settings.get("upscaler_path", ""))
        self.worker: ImageEnhanceWorker | None = None

        layout = QVBoxLayout(self); layout.setContentsMargins(22, 17, 22, 20); layout.setSpacing(12)
        self.title = QLabel(); self.title.setObjectName("pageTitle"); layout.addWidget(self.title)
        self.subtitle = QLabel(); self.subtitle.setObjectName("muted"); self.subtitle.setWordWrap(True); layout.addWidget(self.subtitle)
        card = QFrame(); card.setObjectName("toolbar")
        card_layout = QVBoxLayout(card); card_layout.setContentsMargins(22, 22, 22, 22); card_layout.setSpacing(16)
        card_layout.addStretch()
        self.file_label = QLabel(); self.file_label.setAlignment(Qt.AlignCenter); self.file_label.setWordWrap(True); card_layout.addWidget(self.file_label)
        options = QHBoxLayout(); options.addStretch()
        self.style_label = QLabel(); options.addWidget(self.style_label)
        self.style_combo = QComboBox(); self.style_combo.setObjectName("repairMode")
        for value in ("photo", "art"): self.style_combo.addItem("", value)
        options.addWidget(self.style_combo); options.addSpacing(14)
        self.noise_label = QLabel(); options.addWidget(self.noise_label)
        self.noise_combo = QComboBox(); self.noise_combo.setObjectName("repairMode")
        for value in ("none", "low", "medium", "high"): self.noise_combo.addItem("", value)
        self.noise_combo.setCurrentIndex(1); options.addWidget(self.noise_combo); options.addSpacing(14)
        self.scale_label = QLabel(); options.addWidget(self.scale_label)
        self.scale_combo = QComboBox(); self.scale_combo.setObjectName("repairMode")
        for value in (2, 4): self.scale_combo.addItem("", value)
        options.addWidget(self.scale_combo); options.addStretch(); card_layout.addLayout(options)
        engine_row = QHBoxLayout(); engine_row.addStretch(); self.engine_label = QLabel(); self.engine_label.setObjectName("muted"); engine_row.addWidget(self.engine_label)
        self.engine_btn = QPushButton(); self.engine_btn.clicked.connect(self.choose_engine); engine_row.addWidget(self.engine_btn)
        self.download_btn = QPushButton(); self.download_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://huggingface.co/microsoft/dml-ai-hub-models/resolve/main/real_esrgan_x4plus/real_esrgan_x4plus.onnx?download=true"))); engine_row.addWidget(self.download_btn); engine_row.addStretch(); card_layout.addLayout(engine_row)
        self.hint = QLabel(); self.hint.setObjectName("muted"); self.hint.setAlignment(Qt.AlignCenter); self.hint.setWordWrap(True); card_layout.addWidget(self.hint)
        buttons = QHBoxLayout(); buttons.addStretch()
        self.choose_btn = QPushButton(); self.choose_btn.setObjectName("primary"); self.choose_btn.clicked.connect(self.choose_image); buttons.addWidget(self.choose_btn)
        self.enhance_btn = QPushButton(); self.enhance_btn.clicked.connect(self.enhance_image); buttons.addWidget(self.enhance_btn)
        self.open_btn = QPushButton(); self.open_btn.clicked.connect(self.save_output); buttons.addWidget(self.open_btn)
        buttons.addStretch(); card_layout.addLayout(buttons)
        self.progress = QProgressBar(); self.progress.setRange(0, 100); self.progress.setTextVisible(False); card_layout.addWidget(self.progress)
        self.status = QLabel(); self.status.setObjectName("muted"); self.status.setAlignment(Qt.AlignCenter); card_layout.addWidget(self.status)
        card_layout.addStretch(); layout.addWidget(card, 1)
        self.retranslate(); self.update_actions()

    def retranslate(self) -> None:
        t = self.window.tr
        self.title.setText(t("enhance_title")); self.subtitle.setText(t("enhance_subtitle"))
        self.style_label.setText(t("enhance_style"))
        for index, key in enumerate(("style_photo", "style_art")): self.style_combo.setItemText(index, t(key))
        self.noise_label.setText(t("enhance_noise"))
        for index, key in enumerate(("noise_none", "noise_low", "noise_medium", "noise_high")): self.noise_combo.setItemText(index, t(key))
        self.scale_label.setText(t("enhance_scale"))
        for index, key in enumerate(("scale_2x", "scale_4x")): self.scale_combo.setItemText(index, t(key))
        self.engine_btn.setText(t("choose_enhance_engine")); self.download_btn.setText(t("download_enhance_engine"))
        self.hint.setText(t("enhance_hint")); self.choose_btn.setText(t("choose_enhance_image"))
        self.enhance_btn.setText(t("start_enhance")); self.open_btn.setText(t("save_result"))
        if self.source_path is None: self.file_label.setText(t("no_enhance_image"))
        self.update_engine_label()

    def resolved_engine(self) -> Path | None:
        try: return ImageEnhancer.resolve_engine(self.engine_path or None)
        except FileNotFoundError: return None

    def update_engine_label(self) -> None:
        engine = self.resolved_engine()
        self.engine_label.setText(self.window.tr("enhance_engine_ready").format(name=engine.parent.name) if engine else self.window.tr("enhance_engine_missing"))

    def choose_engine(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, self.window.tr("choose_enhance_engine"), "", self.window.tr("enhance_engine_filter"))
        if not path: return
        self.engine_path = path; self.window.settings["upscaler_path"] = path; self.window.save_settings(); self.update_engine_label(); self.update_actions()

    def update_actions(self) -> None:
        busy = self.worker is not None
        self.choose_btn.setEnabled(not busy); self.style_combo.setEnabled(not busy); self.noise_combo.setEnabled(not busy); self.scale_combo.setEnabled(not busy)
        self.engine_btn.setEnabled(not busy); self.download_btn.setEnabled(not busy)
        self.enhance_btn.setEnabled(self.source_path is not None and self.resolved_engine() is not None and not busy)
        self.open_btn.setEnabled(self.output_path is not None and not busy)

    def choose_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, self.window.tr("choose_enhance_image"), "", self.window.tr("image_filter"))
        if not path: return
        try:
            with Image.open(path) as image:
                if getattr(image, "is_animated", False): raise ValueError("Animated images are not supported.")
                dimensions = f"{image.width}×{image.height}"
        except Exception as exc:
            QMessageBox.critical(self, self.window.tr("open_failed"), str(exc)); return
        discard_staged_output(self.output_path); self.source_path = path; self.output_path = None; self.progress.setValue(0); self.status.setText("")
        self.file_label.setText(f"{Path(path).name}\n{dimensions}"); self.update_actions()

    def enhance_image(self) -> None:
        if self.worker is not None or self.source_path is None: return
        discard_staged_output(self.output_path); self.output_path = None; self.progress.setRange(0, 0); self.status.setText(self.window.tr("enhancing"))
        engine = self.resolved_engine()
        if engine is None: return
        self.worker = ImageEnhanceWorker(self.source_path, str(engine), str(self.style_combo.currentData()), str(self.noise_combo.currentData()), int(self.scale_combo.currentData()), self)
        self.worker.succeeded.connect(self.on_succeeded); self.worker.failed.connect(self.on_failed)
        self.worker.finished.connect(self.on_finished); self.worker.start(); self.update_actions()

    def on_succeeded(self, output_path: str, before_w: int, before_h: int, after_w: int, after_h: int) -> None:
        self.output_path = output_path
        self.status.setText(self.window.tr("enhance_done").format(name=Path(output_path).name, before=f"{before_w}×{before_h}", after=f"{after_w}×{after_h}"))

    def on_failed(self, message: str) -> None:
        self.status.setText(self.window.tr("enhance_failed")); QMessageBox.critical(self, self.window.tr("enhance_failed"), message)

    def on_finished(self) -> None:
        self.progress.setRange(0, 100); self.progress.setValue(100 if self.output_path else 0)
        worker = self.worker; self.worker = None
        if worker is not None: worker.deleteLater()
        self.update_actions()

    def save_output(self) -> None:
        if not self.output_path or not self.source_path: return
        staged = self.output_path; suggested = str(Path(self.source_path).with_name(Path(staged).name))
        saved = save_staged_file(self, staged, self.window.tr("save_result_title"), suggested, self.window.tr("png_filter"))
        if saved:
            discard_staged_output(staged); self.output_path = None
            self.status.setText(self.window.tr("saved").format(name=Path(saved).name)); self.update_actions()


class IdPhotoWorker(QThread):
    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, source_path: str, model_path: str, primary: str, secondary: str, gradient: bool, photo_size: str, parent=None) -> None:
        super().__init__(parent)
        self.source_path = source_path; self.model_path = model_path
        self.primary = primary; self.secondary = secondary; self.gradient = gradient; self.photo_size = photo_size

    def run(self) -> None:
        stage = staged_output_dir()
        try:
            output = IdPhotoGenerator().generate(
                self.source_path, self.model_path, self.primary, self.secondary,
                self.gradient, stage, self.photo_size,
            )
            self.succeeded.emit(str(output))
        except Exception as exc:
            shutil.rmtree(stage, ignore_errors=True)
            self.failed.emit(str(exc))


class IdPhotoPanel(QWidget):
    MODEL_URL = "https://github.com/yakhyo/modnet/releases/download/weights/modnet_photographic.onnx"

    def __init__(self, window) -> None:
        super().__init__()
        self.window = window
        self.source_path: str | None = None; self.output_path: str | None = None
        self.model_path = str(window.settings.get("id_photo_model", ""))
        self.primary = "#438EDB"; self.secondary = "#EAF6FF"
        self.worker: IdPhotoWorker | None = None

        layout = QVBoxLayout(self); layout.setContentsMargins(22, 17, 22, 20); layout.setSpacing(12)
        self.title = QLabel(); self.title.setObjectName("pageTitle"); layout.addWidget(self.title)
        self.subtitle = QLabel(); self.subtitle.setObjectName("muted"); layout.addWidget(self.subtitle)
        card = QFrame(); card.setObjectName("toolbar"); card_layout = QHBoxLayout(card); card_layout.setContentsMargins(20, 18, 20, 18); card_layout.setSpacing(20)
        controls = QVBoxLayout(); controls.setSpacing(12)
        self.file_label = QLabel(); self.file_label.setWordWrap(True); controls.addWidget(self.file_label)
        size_row = QHBoxLayout(); self.size_label = QLabel(); size_row.addWidget(self.size_label)
        self.size_combo = QComboBox(); self.size_combo.setObjectName("repairMode")
        self.size_combo.addItem("", "one_inch"); self.size_combo.addItem("", "two_inch")
        size_row.addWidget(self.size_combo, 1); controls.addLayout(size_row)
        background_row = QHBoxLayout(); self.background_label = QLabel(); background_row.addWidget(self.background_label)
        self.background_combo = QComboBox(); self.background_combo.setObjectName("repairMode")
        for value in ("blue", "red", "white", "gradient", "custom"): self.background_combo.addItem("", value)
        self.background_combo.currentIndexChanged.connect(self.apply_preset); background_row.addWidget(self.background_combo, 1); controls.addLayout(background_row)
        colors = QHBoxLayout(); self.primary_btn = QPushButton(); self.primary_btn.clicked.connect(lambda: self.choose_color(False)); colors.addWidget(self.primary_btn)
        self.secondary_btn = QPushButton(); self.secondary_btn.clicked.connect(lambda: self.choose_color(True)); colors.addWidget(self.secondary_btn); controls.addLayout(colors)
        model_row = QHBoxLayout(); self.model_label = QLabel(); self.model_label.setObjectName("muted"); model_row.addWidget(self.model_label, 1)
        self.model_btn = QPushButton(); self.model_btn.clicked.connect(self.choose_model); model_row.addWidget(self.model_btn)
        self.download_btn = QPushButton(); self.download_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.MODEL_URL))); model_row.addWidget(self.download_btn); controls.addLayout(model_row)
        self.model_hint = QLabel(); self.model_hint.setObjectName("muted"); controls.addWidget(self.model_hint)
        actions = QHBoxLayout(); self.choose_btn = QPushButton(); self.choose_btn.setObjectName("primary"); self.choose_btn.clicked.connect(self.choose_image); actions.addWidget(self.choose_btn)
        self.generate_btn = QPushButton(); self.generate_btn.clicked.connect(self.generate_photo); actions.addWidget(self.generate_btn)
        self.open_btn = QPushButton(); self.open_btn.clicked.connect(self.save_output); actions.addWidget(self.open_btn); controls.addLayout(actions)
        self.progress = QProgressBar(); self.progress.setRange(0, 100); self.progress.setTextVisible(False); controls.addWidget(self.progress)
        self.status = QLabel(); self.status.setObjectName("muted"); self.status.setWordWrap(True); controls.addWidget(self.status); controls.addStretch()
        card_layout.addLayout(controls, 3)
        self.preview = QLabel(); self.preview.setAlignment(Qt.AlignCenter); self.preview.setMinimumSize(250, 330); self.preview.setObjectName("previewCard"); card_layout.addWidget(self.preview, 2)
        layout.addWidget(card, 1)
        self.retranslate(); self.apply_preset(); self.update_actions()

    def resolved_model(self) -> Path | None:
        try: return IdPhotoGenerator.resolve_model(self.model_path or None)
        except FileNotFoundError: return None

    def update_model_label(self) -> None:
        model = self.resolved_model()
        self.model_label.setText(self.window.tr("id_model_ready").format(name=model.name) if model else self.window.tr("id_model_missing"))

    def retranslate(self) -> None:
        t = self.window.tr; self.title.setText(t("id_photo_title")); self.subtitle.setText(t("id_photo_subtitle"))
        self.size_label.setText(t("id_photo_size")); self.size_combo.setItemText(0, t("one_inch")); self.size_combo.setItemText(1, t("two_inch"))
        self.background_label.setText(t("id_background"))
        for index, key in enumerate(("background_blue", "background_red", "background_white", "background_gradient", "background_custom")): self.background_combo.setItemText(index, t(key))
        self.primary_btn.setText(t("primary_color")); self.secondary_btn.setText(t("secondary_color"))
        self.model_btn.setText(t("choose_id_model")); self.download_btn.setText(t("download_id_model")); self.model_hint.setText(t("id_model_hint"))
        self.choose_btn.setText(t("choose_id_photo")); self.generate_btn.setText(t("generate_id_photo")); self.open_btn.setText(t("save_result"))
        if self.source_path is None:
            self.file_label.setText(t("no_id_photo")); self.preview.setText(t("no_id_photo"))
        self.update_model_label(); self.update_color_buttons()

    def apply_preset(self) -> None:
        preset = self.background_combo.currentData()
        if preset == "blue": self.primary, self.secondary = "#438EDB", "#438EDB"
        elif preset == "red": self.primary, self.secondary = "#D92D32", "#D92D32"
        elif preset == "white": self.primary, self.secondary = "#FFFFFF", "#FFFFFF"
        elif preset == "gradient": self.primary, self.secondary = "#4B9BE8", "#EAF6FF"
        self.update_color_buttons(); self.secondary_btn.setVisible(preset == "gradient")

    def update_color_buttons(self) -> None:
        def style(value: str) -> str:
            color = QColor(value)
            foreground = "#ffffff" if color.lightness() < 145 else "#252525"
            return f"background:{value}; color:{foreground}; border:1px solid #b8b8bd;"

        self.primary_btn.setStyleSheet(style(self.primary))
        self.secondary_btn.setStyleSheet(style(self.secondary))

    def choose_color(self, secondary: bool) -> None:
        initial = QColor(self.secondary if secondary else self.primary)
        color = QColorDialog.getColor(initial, self, self.window.tr("choose_color"))
        if not color.isValid(): return
        if secondary: self.secondary = color.name()
        else: self.primary = color.name()
        if self.background_combo.currentData() != "gradient": self.background_combo.setCurrentIndex(4)
        self.update_color_buttons()

    def choose_model(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, self.window.tr("choose_id_model"), "", self.window.tr("id_model_filter"))
        if path:
            self.model_path = path; self.window.settings["id_photo_model"] = path; self.window.save_settings(); self.update_model_label(); self.update_actions()

    def choose_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, self.window.tr("choose_id_photo"), "", self.window.tr("image_filter"))
        if not path: return
        try:
            pixmap = QPixmap(path)
            if pixmap.isNull(): raise ValueError("Unsupported image")
        except Exception as exc:
            QMessageBox.critical(self, self.window.tr("open_failed"), str(exc)); return
        discard_staged_output(self.output_path); self.source_path = path; self.output_path = None; self.file_label.setText(Path(path).name)
        self.preview.setText(""); self.preview.setPixmap(pixmap.scaled(self.preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)); self.status.setText(""); self.update_actions()

    def update_actions(self) -> None:
        busy = self.worker is not None
        for widget in (self.choose_btn, self.model_btn, self.download_btn, self.size_combo, self.background_combo, self.primary_btn, self.secondary_btn): widget.setEnabled(not busy)
        self.generate_btn.setEnabled(self.source_path is not None and self.resolved_model() is not None and not busy)
        self.open_btn.setEnabled(self.output_path is not None and not busy)

    def generate_photo(self) -> None:
        model = self.resolved_model()
        if self.worker is not None or self.source_path is None or model is None: return
        gradient = self.background_combo.currentData() == "gradient"
        discard_staged_output(self.output_path); self.output_path = None; self.progress.setRange(0, 0); self.status.setText(self.window.tr("generating_id_photo"))
        self.worker = IdPhotoWorker(
            self.source_path, str(model), self.primary, self.secondary, gradient,
            str(self.size_combo.currentData()), self,
        )
        self.worker.succeeded.connect(self.on_succeeded); self.worker.failed.connect(self.on_failed); self.worker.finished.connect(self.on_finished)
        self.worker.start(); self.update_actions()

    def on_succeeded(self, output_path: str) -> None:
        self.output_path = output_path; pixmap = QPixmap(output_path)
        self.preview.setPixmap(pixmap.scaled(self.preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.status.setText(self.window.tr("result_ready"))

    def on_failed(self, message: str) -> None:
        self.status.setText(self.window.tr("id_photo_failed")); QMessageBox.critical(self, self.window.tr("id_photo_failed"), message)

    def on_finished(self) -> None:
        self.progress.setRange(0, 100); self.progress.setValue(100 if self.output_path else 0)
        worker = self.worker; self.worker = None
        if worker is not None: worker.deleteLater()
        self.update_actions()

    def save_output(self) -> None:
        if not self.output_path or not self.source_path: return
        staged = self.output_path; suggested = str(Path(self.source_path).with_name(Path(staged).name))
        saved = save_staged_file(self, staged, self.window.tr("save_result_title"), suggested, self.window.tr("png_filter"))
        if saved:
            discard_staged_output(staged); self.output_path = None
            self.status.setText(self.window.tr("saved").format(name=Path(saved).name)); self.update_actions()


class CajConvertWorker(QThread):
    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, source_path: str, parent=None) -> None:
        super().__init__(parent)
        self.source_path = source_path

    def run(self) -> None:
        stage = staged_output_dir()
        try:
            output = CajToPdfConverter().convert(self.source_path, stage)
            self.succeeded.emit(str(output))
        except Exception as exc:
            shutil.rmtree(stage, ignore_errors=True)
            self.failed.emit(str(exc))


class CajToPdfPanel(QWidget):
    def __init__(self, window) -> None:
        super().__init__()
        self.window = window
        self.source_path: str | None = None
        self.output_path: str | None = None
        self.worker: CajConvertWorker | None = None

        layout = QVBoxLayout(self); layout.setContentsMargins(22, 17, 22, 20); layout.setSpacing(12)
        self.title = QLabel(); self.title.setObjectName("pageTitle"); layout.addWidget(self.title)
        self.subtitle = QLabel(); self.subtitle.setObjectName("muted"); self.subtitle.setWordWrap(True); layout.addWidget(self.subtitle)
        card = QFrame(); card.setObjectName("toolbar")
        card_layout = QVBoxLayout(card); card_layout.setContentsMargins(22, 22, 22, 22); card_layout.setSpacing(14)
        card_layout.addStretch()
        self.file_label = QLabel(); self.file_label.setAlignment(Qt.AlignCenter); self.file_label.setWordWrap(True); card_layout.addWidget(self.file_label)
        buttons = QHBoxLayout(); buttons.addStretch()
        self.choose_btn = QPushButton(); self.choose_btn.setObjectName("primary"); self.choose_btn.clicked.connect(self.choose_file); buttons.addWidget(self.choose_btn)
        self.convert_btn = QPushButton(); self.convert_btn.clicked.connect(self.convert_file); buttons.addWidget(self.convert_btn)
        self.open_btn = QPushButton(); self.open_btn.clicked.connect(self.save_output); buttons.addWidget(self.open_btn)
        buttons.addStretch(); card_layout.addLayout(buttons)
        self.progress = QProgressBar(); self.progress.setRange(0, 100); self.progress.setTextVisible(False); card_layout.addWidget(self.progress)
        self.status = QLabel(); self.status.setObjectName("muted"); self.status.setAlignment(Qt.AlignCenter); card_layout.addWidget(self.status)
        card_layout.addStretch(); layout.addWidget(card, 1)
        self.retranslate(); self.update_actions()

    def retranslate(self) -> None:
        t = self.window.tr
        self.title.setText(t("caj_title")); self.subtitle.setText(t("caj_subtitle"))
        self.choose_btn.setText(t("choose_caj")); self.convert_btn.setText(t("convert_caj")); self.open_btn.setText(t("save_result"))
        if self.source_path is None: self.file_label.setText(t("no_caj"))

    def update_actions(self) -> None:
        busy = self.worker is not None
        self.choose_btn.setEnabled(not busy)
        self.convert_btn.setEnabled(self.source_path is not None and not busy)
        self.open_btn.setEnabled(self.output_path is not None and not busy)

    def choose_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, self.window.tr("choose_caj"), "", self.window.tr("caj_filter"))
        if not path: return
        discard_staged_output(self.output_path); self.source_path = path; self.output_path = None; self.progress.setRange(0, 100); self.progress.setValue(0); self.status.setText("")
        self.file_label.setText(f"{Path(path).name}\n{path}"); self.update_actions()

    def convert_file(self) -> None:
        if self.worker is not None or self.source_path is None: return
        discard_staged_output(self.output_path); self.output_path = None; self.progress.setRange(0, 0); self.status.setText(self.window.tr("caj_converting"))
        self.worker = CajConvertWorker(self.source_path, self)
        self.worker.succeeded.connect(self.on_succeeded); self.worker.failed.connect(self.on_failed)
        self.worker.finished.connect(self.on_finished); self.worker.start(); self.update_actions()

    def on_succeeded(self, output_path: str) -> None:
        self.output_path = output_path
        self.status.setText(self.window.tr("result_ready"))

    def on_failed(self, message: str) -> None:
        self.status.setText(self.window.tr("caj_failed"))
        QMessageBox.critical(self, self.window.tr("caj_failed"), message)

    def on_finished(self) -> None:
        self.progress.setRange(0, 100); self.progress.setValue(100 if self.output_path else 0)
        worker = self.worker; self.worker = None
        if worker is not None: worker.deleteLater()
        self.update_actions()

    def save_output(self) -> None:
        if not self.output_path or not self.source_path: return
        staged = self.output_path; suggested = str(Path(self.source_path).with_suffix(".pdf"))
        saved = save_staged_file(self, staged, self.window.tr("save_result_title"), suggested, "PDF (*.pdf)")
        if saved:
            discard_staged_output(staged); self.output_path = None
            self.status.setText(self.window.tr("saved").format(name=Path(saved).name)); self.update_actions()


class ImageCanvas(QWidget):
    mask_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("themeRoot")
        self.setMinimumHeight(320)
        self.setCursor(Qt.CrossCursor)
        self.image: Image.Image | None = None
        self.mask: Image.Image | None = None
        self.brush = 32
        self.last_point: tuple[int, int] | None = None
        self.before_stroke: tuple[Image.Image, Image.Image] | None = None
        self.hint = TEXT["zh"]["canvas_hint"]
        self.setMouseTracking(True)

    def set_images(self, image: Image.Image, mask: Image.Image) -> None:
        self.image, self.mask = image, mask
        self.update()

    def image_rect(self) -> QRectF:
        if self.image is None:
            return QRectF()
        scale = min((self.width() - 32) / self.image.width, (self.height() - 32) / self.image.height, 1.0)
        width, height = self.image.width * scale, self.image.height * scale
        return QRectF((self.width() - width) / 2, (self.height() - height) / 2, width, height)

    def event_point(self, position) -> tuple[int, int] | None:
        if self.image is None:
            return None
        rect = self.image_rect()
        if not rect.contains(position):
            return None
        return int((position.x() - rect.x()) * self.image.width / rect.width()), int((position.y() - rect.y()) * self.image.height / rect.height())

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self.image is None:
            painter.setPen(QColor("#8d8d92"))
            painter.drawText(self.rect(), Qt.AlignCenter, self.hint)
            return
        rect = self.image_rect()
        painter.drawPixmap(rect, pil_to_pixmap(self.image), QRectF(0, 0, self.image.width, self.image.height))
        if self.mask and self.mask.getbbox():
            overlay = Image.new("RGBA", self.image.size, (236, 65, 65, 0))
            overlay.putalpha(self.mask.point(lambda value: int(value * .58)))
            painter.drawPixmap(rect, pil_to_pixmap(overlay), QRectF(0, 0, self.image.width, self.image.height))

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.LeftButton or self.image is None or self.mask is None:
            return
        point = self.event_point(event.position())
        if point is None:
            return
        self.before_stroke = (self.image.copy(), self.mask.copy())
        self.last_point = point
        self._paint(point, point)

    def mouseMoveEvent(self, event) -> None:
        if not (event.buttons() & Qt.LeftButton) or self.last_point is None:
            return
        point = self.event_point(event.position())
        if point is not None:
            self._paint(self.last_point, point)
            self.last_point = point

    def mouseReleaseEvent(self, _event) -> None:
        self.last_point = None

    def _paint(self, start, end) -> None:
        draw = ImageDraw.Draw(self.mask)
        rect = self.image_rect()
        width = max(2, int(self.brush * self.image.width / rect.width()))
        draw.line((start, end), fill=255, width=width)
        radius = width // 2
        draw.ellipse((end[0] - radius, end[1] - radius, end[0] + radius, end[1] + radius), fill=255)
        self.mask_changed.emit()
        self.update()


class TitleBar(QWidget):
    theme_clicked = Signal()

    def __init__(self, window) -> None:
        super().__init__()
        self.window = window
        self.drag_offset = QPoint()
        self.setFixedHeight(44)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 5, 0)
        logo = QLabel("N")
        logo.setObjectName("logo")
        logo.setFixedSize(25, 25)
        logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo)
        self.name_label = QLabel()
        layout.addWidget(self.name_label)
        layout.addStretch()
        self.theme_button = QPushButton()
        self.theme_button.setObjectName("windowButton")
        self.theme_button.clicked.connect(self.theme_clicked)
        self.theme_button.setFixedSize(34, 34); self.theme_button.setIconSize(QSize(18, 18))
        layout.addWidget(self.theme_button)
        self.control_buttons = {}
        for kind, callback in (("minimize", window.showMinimized), ("maximize", window.toggle_maximize), ("close", window.close)):
            button = QPushButton()
            button.setObjectName("closeButton" if kind == "close" else "windowButton")
            button.setFixedSize(34, 34); button.setIconSize(QSize(18, 18))
            button.clicked.connect(callback)
            self.control_buttons[kind] = button
            layout.addWidget(button)
        self.retranslate()

    def retranslate(self) -> None:
        self.name_label.setText(self.window.tr("app"))

    def update_icons(self) -> None:
        color = PALETTES[self.window.theme]["text"]
        self.theme_button.setIcon(window_control_icon("sun" if self.window.theme == "dark" else "moon", color))
        for kind, button in self.control_buttons.items():
            button.setIcon(window_control_icon(kind, color))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.drag_offset = event.globalPosition().toPoint() - self.window.frameGeometry().topLeft()

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.LeftButton and not self.window.isMaximized():
            self.window.move(event.globalPosition().toPoint() - self.drag_offset)

    def mouseDoubleClickEvent(self, _event) -> None:
        self.window.toggle_maximize()


class SettingsDialog(QDialog):
    def __init__(self, window) -> None:
        super().__init__(window)
        self.window = window
        self.setFixedSize(440, 300)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        self.language_title = QLabel()
        self.language_title.setObjectName("pageTitle")
        layout.addWidget(self.language_title)
        self.language_combo = QComboBox()
        self.language_combo.setObjectName("repairMode")
        self.language_combo.addItem("简体中文", "zh")
        self.language_combo.addItem("English", "en")
        self.language_combo.setCurrentIndex(max(0, self.language_combo.findData(window.language)))
        self.language_combo.currentIndexChanged.connect(self.change_language)
        layout.addWidget(self.language_combo)
        layout.addStretch()
        divider = QFrame(); divider.setFrameShape(QFrame.HLine); divider.setObjectName("settingsDivider")
        layout.addWidget(divider)
        self.about_title = QLabel(); self.about_title.setObjectName("pageTitle"); layout.addWidget(self.about_title)
        self.version_label = QLabel(); layout.addWidget(self.version_label)
        self.copyright_label = QLabel(); self.copyright_label.setObjectName("muted"); layout.addWidget(self.copyright_label)
        self.retranslate()
        self.window._repolish_theme(self)

    def change_language(self) -> None:
        self.window.set_language(self.language_combo.currentData())
        self.retranslate()

    def retranslate(self) -> None:
        t = self.window.tr
        self.setWindowTitle(t("settings_title"))
        self.language_title.setText(t("language"))
        self.about_title.setText(t("about"))
        self.version_label.setText(t("version_info").format(version=APP_VERSION))
        self.copyright_label.setText(t("copyright_info").format(year=COPYRIGHT_YEAR, owner=COPYRIGHT_OWNER))

class NiuBToolbox(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowIcon(QIcon(str(resource_path("assets/app-icon.ico"))))
        self.setMinimumSize(820, 560)
        self.resize(980, 680)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        config_root = Path(os.getenv("NIUB_CONFIG_DIR", Path(os.getenv("APPDATA", Path.home())) / "NiuBToolbox"))
        self.config_path = config_root / "config.json"
        self.settings = self.load_settings()
        self.theme = self.settings.get("theme", "light")
        self.language = self.settings.get("language", "zh")
        if self.language not in TEXT:
            self.language = "zh"
        InpaintEngine.set_model_path(self.settings.get("model_path"))
        self.history: list[tuple[Image.Image, Image.Image]] = []
        self.image: Image.Image | None = None
        self.mask: Image.Image | None = None
        self.repair_worker: RepairWorker | None = None
        self._resize_drag: tuple[Qt.Edges, QPoint, QRect] | None = None
        self._build_ui()
        self._create_resize_handles()
        QApplication.instance().installEventFilter(self)
        self.apply_theme()
        self.retranslate()

    def _build_ui(self) -> None:
        host = QWidget()
        host_layout = QVBoxLayout(host)
        host_layout.setContentsMargins(12, 12, 12, 12)
        self.card = QFrame()
        self.card.setObjectName("windowCard")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28); shadow.setOffset(0, 6); shadow.setColor(QColor(0, 0, 0, 80))
        self.card.setGraphicsEffect(shadow)
        host_layout.addWidget(self.card)
        root = QVBoxLayout(self.card); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
        self.titlebar = TitleBar(self); self.titlebar.theme_clicked.connect(self.toggle_theme); root.addWidget(self.titlebar)
        body = QHBoxLayout(); body.setContentsMargins(0, 0, 0, 0); body.setSpacing(0); root.addLayout(body)

        side = QFrame(); side.setObjectName("sidebar"); side.setFixedWidth(210); self.sidebar = side
        side_layout = QVBoxLayout(side); side_layout.setContentsMargins(12, 22, 12, 14)
        self.tools_label = QLabel(); self.tools_label.setObjectName("muted"); side_layout.addWidget(self.tools_label)
        self.active_btn = QPushButton(); self.active_btn.setObjectName("navButton"); self.active_btn.setCheckable(True)
        self.active_btn.clicked.connect(lambda: self.show_tool(0)); side_layout.addWidget(self.active_btn)
        self.compress_btn = QPushButton(); self.compress_btn.setObjectName("navButton"); self.compress_btn.setCheckable(True)
        self.compress_btn.clicked.connect(lambda: self.show_tool(1)); side_layout.addWidget(self.compress_btn)
        self.enhance_btn = QPushButton(); self.enhance_btn.setObjectName("navButton"); self.enhance_btn.setCheckable(True)
        self.enhance_btn.clicked.connect(lambda: self.show_tool(2)); side_layout.addWidget(self.enhance_btn)
        self.id_photo_btn = QPushButton(); self.id_photo_btn.setObjectName("navButton"); self.id_photo_btn.setCheckable(True)
        self.id_photo_btn.clicked.connect(lambda: self.show_tool(3)); side_layout.addWidget(self.id_photo_btn)
        side_layout.addSpacing(12)
        self.file_tools_label = QLabel(); self.file_tools_label.setObjectName("muted"); side_layout.addWidget(self.file_tools_label)
        self.pdf_btn = QPushButton(); self.pdf_btn.setObjectName("navButton"); self.pdf_btn.setCheckable(True)
        self.pdf_btn.clicked.connect(lambda: self.show_tool(4)); side_layout.addWidget(self.pdf_btn)
        self.caj_btn = QPushButton(); self.caj_btn.setObjectName("navButton"); self.caj_btn.setCheckable(True)
        self.caj_btn.clicked.connect(lambda: self.show_tool(5)); side_layout.addWidget(self.caj_btn)
        self.media_btn = QPushButton(); self.media_btn.setObjectName("navButton"); self.media_btn.setCheckable(True)
        self.media_btn.clicked.connect(lambda: self.show_tool(6)); side_layout.addWidget(self.media_btn)
        side_layout.addStretch()
        self.settings_btn = QPushButton("⚙   设置"); self.settings_btn.clicked.connect(lambda: SettingsDialog(self).exec()); side_layout.addWidget(self.settings_btn)
        self.privacy_label = QLabel(); self.privacy_label.setObjectName("muted"); side_layout.addWidget(self.privacy_label)
        body.addWidget(side)

        content = QWidget(); content_layout = QVBoxLayout(content); content_layout.setContentsMargins(22, 17, 22, 20); content_layout.setSpacing(10)
        heading = QHBoxLayout(); self.page_title = QLabel(); self.page_title.setObjectName("pageTitle"); heading.addWidget(self.page_title)
        self.subtitle = QLabel(); self.subtitle.setObjectName("muted"); heading.addWidget(self.subtitle); heading.addStretch()
        self.delete_image_btn = QPushButton()
        self.delete_image_btn.clicked.connect(self.delete_image)
        heading.addWidget(self.delete_image_btn)
        self.choose_btn = QPushButton(); self.choose_btn.setObjectName("primary"); self.choose_btn.clicked.connect(self.open_image); heading.addWidget(self.choose_btn); content_layout.addLayout(heading)
        self.canvas = ImageCanvas(); self.canvas.setObjectName("imageCanvas"); self.canvas.mask_changed.connect(self.mask_changed); content_layout.addWidget(self.canvas, 1)

        toolbar = QFrame(); toolbar.setObjectName("toolbar"); tool = QVBoxLayout(toolbar); tool.setContentsMargins(14, 9, 14, 9); tool.setSpacing(7)
        top = QHBoxLayout(); self.brush_label = QLabel(); top.addWidget(self.brush_label); slider = QSlider(Qt.Horizontal); slider.setRange(8, 120); slider.setValue(32); slider.setFixedWidth(145); slider.valueChanged.connect(lambda value: setattr(self.canvas, "brush", value)); top.addWidget(slider)
        top.addSpacing(14); self.mode_label = QLabel(); top.addWidget(self.mode_label); self.mode = QComboBox(); self.mode.setObjectName("repairMode"); self.mode.setFixedWidth(215); top.addWidget(self.mode); top.addStretch(); self.status = QLabel(); self.status.setObjectName("muted"); top.addWidget(self.status); tool.addLayout(top)
        model_row = QHBoxLayout(); self.watermark_model_title = QLabel(); model_row.addWidget(self.watermark_model_title)
        self.watermark_model_label = QLabel(); self.watermark_model_label.setObjectName("muted"); model_row.addWidget(self.watermark_model_label, 1)
        self.watermark_model_btn = QPushButton(); self.watermark_model_btn.clicked.connect(self.add_watermark_model); model_row.addWidget(self.watermark_model_btn)
        self.watermark_model_reset_btn = QPushButton(); self.watermark_model_reset_btn.clicked.connect(self.reset_watermark_model); model_row.addWidget(self.watermark_model_reset_btn)
        tool.addLayout(model_row)
        actions = QHBoxLayout(); self.undo_btn = QPushButton(); self.undo_btn.clicked.connect(self.undo); actions.addWidget(self.undo_btn); self.clear_btn = QPushButton(); self.clear_btn.clicked.connect(self.clear_mask); actions.addWidget(self.clear_btn); actions.addStretch(); self.export_btn = QPushButton(); self.export_btn.clicked.connect(self.export); actions.addWidget(self.export_btn); self.repair_btn = QPushButton(); self.repair_btn.setObjectName("primary"); self.repair_btn.clicked.connect(self.repair); actions.addWidget(self.repair_btn); tool.addLayout(actions)
        content_layout.addWidget(toolbar)
        self.compress_panel = ImageCompressorPanel(self)
        self.enhance_panel = ImageEnhancerPanel(self)
        self.id_photo_panel = IdPhotoPanel(self)
        self.pdf_panel = PdfToMarkdownPanel(self)
        self.caj_panel = CajToPdfPanel(self)
        self.media_panel = MediaConverterPanel(self)
        self.tool_stack = QStackedWidget(); self.tool_stack.addWidget(content); self.tool_stack.addWidget(self.compress_panel); self.tool_stack.addWidget(self.enhance_panel); self.tool_stack.addWidget(self.id_photo_panel); self.tool_stack.addWidget(self.pdf_panel); self.tool_stack.addWidget(self.caj_panel); self.tool_stack.addWidget(self.media_panel)
        body.addWidget(self.tool_stack, 1)
        self.show_tool(0)
        self.setCentralWidget(host); self.update_actions()

    def show_tool(self, index: int) -> None:
        self.tool_stack.setCurrentIndex(index)
        self.active_btn.setChecked(index == 0)
        self.compress_btn.setChecked(index == 1)
        self.enhance_btn.setChecked(index == 2)
        self.id_photo_btn.setChecked(index == 3)
        self.pdf_btn.setChecked(index == 4)
        self.caj_btn.setChecked(index == 5)
        self.media_btn.setChecked(index == 6)
        if self.styleSheet():
            self._repolish_theme(self.tool_stack.currentWidget())
        self.update_nav_icons()

    def update_nav_icons(self) -> None:
        colors = PALETTES[self.theme]
        buttons = (
            (self.active_btn, "✦"), (self.compress_btn, "▣"), (self.enhance_btn, "◈"), (self.id_photo_btn, "●"),
            (self.pdf_btn, "▤"), (self.caj_btn, "◫"), (self.media_btn, "▶"),
        )
        for button, symbol in buttons:
            button.setIcon(symbol_icon(symbol, colors["red"] if button.isChecked() else colors["text"]))
            button.setIconSize(QSize(18, 18))

    def load_settings(self) -> dict:
        try: return json.loads(self.config_path.read_text(encoding="utf-8"))
        except (OSError, ValueError): return {}

    def save_settings(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps(self.settings, ensure_ascii=False, indent=2), encoding="utf-8")

    def tr(self, key: str) -> str:
        return TEXT[self.language][key]

    def set_language(self, language: str) -> None:
        if language not in TEXT or language == self.language:
            return
        self.language = language
        self.settings["language"] = language
        self.save_settings()
        self.retranslate()

    def retranslate(self) -> None:
        self.setWindowTitle(self.tr("app"))
        QApplication.instance().setApplicationName(self.tr("app"))
        self.titlebar.retranslate()
        self.tools_label.setText(self.tr("image_processing"))
        self.file_tools_label.setText(self.tr("file_processing"))
        self.active_btn.setText(self.tr("watermark"))
        self.compress_btn.setText(self.tr("compress_tool"))
        self.enhance_btn.setText(self.tr("enhance_tool"))
        self.id_photo_btn.setText(self.tr("id_photo_tool"))
        self.pdf_btn.setText(self.tr("pdf_tool"))
        self.caj_btn.setText(self.tr("caj_tool"))
        self.media_btn.setText(self.tr("media_tool"))
        self.settings_btn.setText(self.tr("settings"))
        self.privacy_label.setText(self.tr("local_private"))
        self.page_title.setText(self.tr("watermark"))
        self.subtitle.setText(self.tr("local_process"))
        self.delete_image_btn.setText(self.tr("delete_image"))
        self.choose_btn.setText(self.tr("choose_image"))
        self.canvas.hint = self.tr("canvas_hint")
        self.canvas.update()
        self.brush_label.setText(self.tr("brush_size"))
        self.mode_label.setText(self.tr("repair_mode"))
        selected_mode = self.mode.currentIndex()
        self.mode.blockSignals(True)
        self.mode.clear()
        self.mode.addItems((self.tr("ai_mode"), self.tr("fast_mode")))
        self.mode.setCurrentIndex(max(0, selected_mode))
        self.mode.blockSignals(False)
        self.watermark_model_title.setText(self.tr("watermark_model"))
        self.watermark_model_btn.setText(self.tr("add_model"))
        self.watermark_model_reset_btn.setText(self.tr("reset_model"))
        self.watermark_model_btn.setToolTip(self.tr("model_hint"))
        self.watermark_model_label.setToolTip(self.tr("model_hint"))
        self.update_watermark_model_label()
        self.undo_btn.setText(self.tr("undo"))
        self.clear_btn.setText(self.tr("clear"))
        self.export_btn.setText(self.tr("export"))
        self.repair_btn.setText(self.tr("start_repair"))
        if self.image is None:
            self.status.setText(self.tr("choose_prompt"))
        self.pdf_panel.retranslate()
        self.media_panel.retranslate()
        self.compress_panel.retranslate()
        self.enhance_panel.retranslate()
        self.id_photo_panel.retranslate()
        self.caj_panel.retranslate()

    def toggle_theme(self) -> None:
        self.theme = "dark" if self.theme == "light" else "light"
        self.settings["theme"] = self.theme; self.save_settings(); self.apply_theme()

    def apply_theme(self) -> None:
        p = PALETTES[self.theme]
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(p["window"]))
        palette.setColor(QPalette.Base, QColor(p["card"]))
        palette.setColor(QPalette.AlternateBase, QColor(p["side"]))
        palette.setColor(QPalette.Text, QColor(p["text"]))
        palette.setColor(QPalette.WindowText, QColor(p["text"]))
        palette.setColor(QPalette.ButtonText, QColor(p["text"]))
        palette.setColor(QPalette.PlaceholderText, QColor(p["muted"]))
        palette.setColor(QPalette.Mid, QColor(p["line"]))
        palette.setColor(QPalette.Button, QColor(p["hover"]))
        palette.setColor(QPalette.Dark, QColor(p["canvas"]))
        palette.setColor(QPalette.Highlight, QColor(p["red"]))
        palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        self.setPalette(palette)
        self.setProperty("theme", self.theme)
        self.titlebar.update_icons()
        first_install = not self.styleSheet()
        if first_install:
            arrow_path = (Path(__file__).parent / "assets" / "dropdown-arrow.svg").as_posix()
            color_rules = ""
            for theme_name, colors in PALETTES.items():
                themed = f'[theme="{theme_name}"]'
                color_rules += f"""
                    QWidget{themed} {{ color:{colors['text']}; }}
                    #logo{themed} {{ background:{colors['red']}; color:white; }}
                    #windowCard{themed} {{ background:{colors['card']}; border-color:{colors['line']}; }}
                    #sidebar{themed} {{ background:{colors['side']}; border-right-color:{colors['line']}; }}
                    #muted{themed} {{ color:{colors['muted']}; }}
                    QPushButton{themed} {{ border-color:{colors['line']}; }}
                    QPushButton{themed}:hover {{ background:{colors['hover']}; }}
                    QPushButton{themed}:disabled {{ color:{colors['muted']}; }}
                    #primary{themed} {{ background:{colors['red']}; color:white; }}
                    QPushButton#navButton{themed}:checked {{ background:{colors['hover']}; color:{colors['red']}; }}
                    #closeButton{themed}:hover {{ background:{colors['red']}; color:white; }}
                    #toolbar{themed} {{ background:{colors['card']}; border-color:{colors['line']}; }}
                    #previewCard{themed}, #imageCanvas{themed} {{ background:{colors['canvas']}; border-color:{colors['line']}; }}
                    #settingsDivider{themed} {{ color:{colors['line']}; background:{colors['line']}; }}
                    QComboBox#repairMode{themed} {{ background:{colors['card']}; border-color:{colors['line']}; }}
                    QComboBox#repairMode{themed}:hover {{ background:{colors['hover']}; }}
                    QComboBox#repairMode{themed}:focus {{ border-color:{colors['red']}; }}
                    QComboBox#repairMode{themed} QAbstractItemView {{ background:{colors['card']}; color:{colors['text']}; border-color:{colors['line']}; selection-background-color:{colors['red']}; }}
                    QProgressBar{themed} {{ background:{colors['hover']}; }}
                    QProgressBar{themed}::chunk {{ background:{colors['red']}; }}
                    QDialog{themed} {{ background:{colors['window']}; }}
                """
            self.setStyleSheet(f"""
            QWidget {{ color:palette(text); font-family:'Microsoft YaHei UI'; font-size:13px; }}
            #windowCard {{ background:palette(base); border:1px solid palette(mid); border-radius:18px; }}
            #sidebar {{
                background:palette(alternate-base);
                border-right:1px solid palette(mid);
                border-bottom-left-radius:17px;
            }}
            #logo {{ background:palette(highlight); color:white; border-radius:7px; font-weight:700; }}
            #pageTitle {{ font-size:22px; font-weight:700; }} #muted {{ color:palette(placeholder-text); font-size:11px; }}
            QPushButton {{ background:transparent; border:1px solid palette(mid); border-radius:7px; padding:7px 13px; }} QPushButton:hover {{ background:palette(button); }} QPushButton:disabled {{ color:palette(placeholder-text); }}
            #primary {{ background:palette(highlight); color:white; border:0; font-weight:600; }} #primary:hover {{ background:#d93636; }}
            QPushButton#navButton {{ border:0; text-align:left; padding:10px; }}
            QPushButton#navButton:checked {{ background:palette(button); color:palette(highlight); font-weight:600; }}
            #windowButton, #closeButton {{ border:0; border-radius:6px; min-width:34px; max-width:34px; min-height:34px; max-height:34px; padding:0; }} #closeButton:hover {{ background:palette(highlight); color:white; }}
            #toolbar {{ background:palette(base); border:1px solid palette(mid); border-radius:10px; }}
            #previewCard, #imageCanvas {{ background:palette(dark); border:1px solid palette(mid); border-radius:10px; }}
            #settingsDivider {{ color:palette(mid); background:palette(mid); border:0; max-height:1px; }}
            QComboBox#repairMode {{ background:palette(base); border:1px solid palette(mid); border-radius:9px; padding:6px 36px 6px 12px; min-height:20px; }}
            QComboBox#repairMode:hover {{ border-color:#b8b8bd; background:palette(button); }}
            QComboBox#repairMode:focus {{ border-color:palette(highlight); }}
            QComboBox#repairMode::drop-down {{ subcontrol-origin:padding; subcontrol-position:top right; width:32px; border:0; background:transparent; }}
            QComboBox#repairMode::down-arrow {{ image:url({arrow_path}); width:12px; height:8px; }}
            QComboBox#repairMode QAbstractItemView {{ background:palette(base); color:palette(text); border:1px solid palette(mid); border-radius:9px; padding:5px; outline:0; selection-background-color:palette(highlight); selection-color:white; }}
            QComboBox#repairMode QAbstractItemView::item {{ min-height:30px; padding-left:9px; border-radius:6px; }}
            QProgressBar {{ background:palette(button); border:0; border-radius:4px; min-height:8px; max-height:8px; }}
            QProgressBar::chunk {{ background:palette(highlight); border-radius:4px; }}
            QDialog {{ background:palette(window); }}
            {color_rules}
        """)
        self._repolish_theme(self.titlebar, self.sidebar, self.tool_stack.currentWidget())
        self.update_nav_icons()

    def _repolish_theme(self, *roots: QWidget) -> None:
        widgets: list[QWidget] = [self, self.card]
        for root in roots:
            if root is None: continue
            widgets.append(root); widgets.extend(root.findChildren(QWidget))
        seen: set[int] = set()
        for widget in widgets:
            identity = id(widget)
            if identity in seen: continue
            seen.add(identity)
            widget.setProperty("theme", self.theme)
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            QWidget.update(widget)

    def toggle_maximize(self) -> None:
        self.showNormal() if self.isMaximized() else self.showMaximized()

    def _resize_edges(self, global_position) -> Qt.Edges:
        if self.isMaximized():
            return Qt.Edges()
        point = self.mapFromGlobal(global_position.toPoint())
        # The visible rounded card sits 12 px inside the transparent top-level
        # window. Detect around that visible edge, not around click-through pixels.
        card_margin = 12
        hit_width = 6
        left_edge = card_margin
        right_edge = self.width() - card_margin - 1
        top_edge = card_margin
        bottom_edge = self.height() - card_margin - 1
        edges = Qt.Edges()
        if abs(point.x() - left_edge) <= hit_width:
            edges |= Qt.LeftEdge
        elif abs(point.x() - right_edge) <= hit_width:
            edges |= Qt.RightEdge
        if abs(point.y() - top_edge) <= hit_width:
            edges |= Qt.TopEdge
        elif abs(point.y() - bottom_edge) <= hit_width:
            edges |= Qt.BottomEdge
        return edges

    def _create_resize_handles(self) -> None:
        self.resize_handles: list[QWidget] = []
        definitions = (
            (Qt.LeftEdge, Qt.SizeHorCursor, "left"),
            (Qt.RightEdge, Qt.SizeHorCursor, "right"),
            (Qt.TopEdge, Qt.SizeVerCursor, "top"),
            (Qt.BottomEdge, Qt.SizeVerCursor, "bottom"),
            (Qt.TopEdge | Qt.LeftEdge, Qt.SizeFDiagCursor, "top_left"),
            (Qt.BottomEdge | Qt.LeftEdge, Qt.SizeBDiagCursor, "bottom_left"),
            (Qt.BottomEdge | Qt.RightEdge, Qt.SizeFDiagCursor, "bottom_right"),
        )
        for edges, cursor, name in definitions:
            handle = QWidget(self)
            handle.setObjectName("resizeHandle")
            handle.setProperty("resizeEdges", edges)
            handle.setProperty("resizeName", name)
            handle.setCursor(cursor)
            handle.setStyleSheet("background: transparent;")
            handle.show()
            self.resize_handles.append(handle)
        self._position_resize_handles()

    def _position_resize_handles(self) -> None:
        if not hasattr(self, "resize_handles"):
            return
        width, height = self.width(), self.height()
        geometries = {
            "left": QRect(8, 20, 9, max(0, height - 40)),
            "right": QRect(width - 17, 62, 9, max(0, height - 82)),
            "top": QRect(20, 8, max(0, width - 280), 9),
            "bottom": QRect(20, height - 17, max(0, width - 40), 9),
            "top_left": QRect(8, 8, 13, 13),
            "bottom_left": QRect(8, height - 21, 13, 13),
            "bottom_right": QRect(width - 21, height - 21, 13, 13),
        }
        for handle in self.resize_handles:
            handle.setGeometry(geometries[handle.property("resizeName")])
            handle.raise_()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._position_resize_handles()

    @staticmethod
    def _inside_button(widget) -> bool:
        while widget is not None:
            if isinstance(widget, QPushButton):
                return True
            widget = widget.parentWidget() if hasattr(widget, "parentWidget") else None
        return False

    def eventFilter(self, watched, event) -> bool:
        belongs_to_window = isinstance(watched, QWidget) and (watched is self or self.isAncestorOf(watched))
        if not belongs_to_window:
            return super().eventFilter(watched, event)

        if isinstance(event, QMouseEvent) and event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            if not self._inside_button(watched):
                edges = watched.property("resizeEdges") or self._resize_edges(event.globalPosition())
                if edges:
                    self._resize_drag = (edges, event.globalPosition().toPoint(), self.geometry())
                    self.grabMouse()
                    return True

        if isinstance(event, QMouseEvent) and event.type() == QEvent.MouseMove and self._resize_drag is not None:
            edges, start_position, start_geometry = self._resize_drag
            delta = event.globalPosition().toPoint() - start_position
            geometry = QRect(start_geometry)
            minimum_width = self.minimumWidth()
            minimum_height = self.minimumHeight()
            if edges & Qt.LeftEdge:
                geometry.setLeft(min(start_geometry.left() + delta.x(), start_geometry.right() - minimum_width + 1))
            if edges & Qt.RightEdge:
                geometry.setRight(max(start_geometry.right() + delta.x(), start_geometry.left() + minimum_width - 1))
            if edges & Qt.TopEdge:
                geometry.setTop(min(start_geometry.top() + delta.y(), start_geometry.bottom() - minimum_height + 1))
            if edges & Qt.BottomEdge:
                geometry.setBottom(max(start_geometry.bottom() + delta.y(), start_geometry.top() + minimum_height - 1))
            self.setGeometry(geometry)
            return True

        if isinstance(event, QMouseEvent) and event.type() == QEvent.MouseButtonRelease and self._resize_drag is not None:
            self._resize_drag = None
            self.releaseMouse()
            return True
        return super().eventFilter(watched, event)

    def open_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, self.tr("choose_image"), "", self.tr("image_filter"))
        if not path: return
        try: image = Image.open(path).convert("RGBA")
        except Exception as exc: QMessageBox.critical(self, self.tr("open_failed"), str(exc)); return
        if max(image.size) > 2400: image.thumbnail((2400, 2400), Image.Resampling.LANCZOS)
        self.image = image; self.mask = Image.new("L", image.size, 0); self.history.clear(); self.canvas.set_images(self.image, self.mask); self.status.setText(f"{Path(path).name} · {image.width}×{image.height}"); self.update_actions()

    def mask_changed(self) -> None:
        if self.canvas.before_stroke:
            if not self.history or self.history[-1] != self.canvas.before_stroke: self.history.append(self.canvas.before_stroke)
            self.canvas.before_stroke = None
        self.mask = self.canvas.mask; self.update_actions()

    def update_actions(self) -> None:
        busy = self.repair_worker is not None
        has_mask = self.mask is not None and self.mask.getbbox() is not None
        self.undo_btn.setEnabled(bool(self.history) and not busy); self.clear_btn.setEnabled(has_mask and not busy); self.repair_btn.setEnabled(has_mask and not busy)
        self.delete_image_btn.setEnabled(self.image is not None and not busy)
        self.choose_btn.setEnabled(not busy)
        self.export_btn.setEnabled(self.image is not None and not busy)
        self.settings_btn.setEnabled(not busy)
        self.mode.setEnabled(not busy)
        self.watermark_model_btn.setEnabled(not busy)
        self.watermark_model_reset_btn.setEnabled(bool(self.settings.get("model_path")) and not busy)
        self.canvas.setEnabled(not busy)

    def update_watermark_model_label(self) -> None:
        path = self.settings.get("model_path")
        self.watermark_model_label.setText(Path(path).name if path else self.tr("builtin_model"))

    def add_watermark_model(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, self.tr("add_model_title"), "", self.tr("onnx_filter"))
        if not path: return
        self.settings["model_path"] = path
        self.save_settings()
        InpaintEngine.set_model_path(path)
        self.update_watermark_model_label()
        self.update_actions()

    def reset_watermark_model(self) -> None:
        self.settings.pop("model_path", None)
        self.save_settings()
        InpaintEngine.set_model_path(None)
        self.update_watermark_model_label()
        self.update_actions()

    def delete_image(self) -> None:
        """Remove the image from the workspace without touching the source file."""
        self.image = None
        self.mask = None
        self.history.clear()
        self.canvas.image = None
        self.canvas.mask = None
        self.canvas.before_stroke = None
        self.canvas.last_point = None
        self.canvas.update()
        self.status.setText(self.tr("choose_prompt"))
        self.update_actions()

    def undo(self) -> None:
        if self.history:
            self.image, self.mask = self.history.pop(); self.canvas.set_images(self.image, self.mask); self.update_actions()

    def clear_mask(self) -> None:
        if self.image and self.mask and self.mask.getbbox():
            self.history.append((self.image.copy(), self.mask.copy())); self.mask = Image.new("L", self.image.size, 0); self.canvas.set_images(self.image, self.mask); self.update_actions()

    def repair(self) -> None:
        if self.repair_worker is not None or not self.image or not self.mask or not self.mask.getbbox(): return
        if self.mode.currentIndex() == 0 and not InpaintEngine._model_path().exists():
            QMessageBox.warning(
                self,
                self.tr("model_missing_title"),
                self.tr("model_missing").format(path=InpaintEngine._model_path()),
            )
            return
        self.history.append((self.image.copy(), self.mask.copy()))
        rgba = np.asarray(self.image, dtype=np.uint8).copy()
        binary = np.where(np.asarray(self.mask, dtype=np.uint8) > 8, 255, 0).astype(np.uint8)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.status.setText(self.tr("repairing"))
        self.repair_worker = RepairWorker(rgba, binary, self.mode.currentIndex() == 0, self)
        self.repair_worker.succeeded.connect(self.repair_succeeded)
        self.repair_worker.failed.connect(self.repair_failed)
        self.repair_worker.finished.connect(self.repair_finished)
        self.repair_worker.start()
        self.update_actions()

    def repair_succeeded(self, result: np.ndarray) -> None:
        self.image = Image.fromarray(result, "RGBA")
        self.mask = Image.new("L", self.image.size, 0)
        self.canvas.set_images(self.image, self.mask)
        self.status.setText(self.tr("repair_done"))

    def repair_failed(self, message: str) -> None:
        if self.history:
            self.history.pop()
        QMessageBox.critical(self, self.tr("repair_failed"), message)
        self.status.setText(self.tr("repair_failed"))

    def repair_finished(self) -> None:
        QApplication.restoreOverrideCursor()
        worker = self.repair_worker
        self.repair_worker = None
        if worker is not None:
            worker.deleteLater()
        self.update_actions()

    def closeEvent(self, event) -> None:
        if self.repair_worker is not None:
            self.status.setText(self.tr("wait_close"))
            event.ignore()
            return
        if self.pdf_panel.worker is not None:
            self.pdf_panel.status.setText(self.tr("wait_close_pdf"))
            event.ignore()
            return
        if self.media_panel.worker is not None:
            self.media_panel.status.setText(self.tr("wait_close_media"))
            event.ignore()
            return
        if self.compress_panel.worker is not None:
            self.compress_panel.status.setText(self.tr("wait_close_compress"))
            event.ignore()
            return
        if self.enhance_panel.worker is not None:
            self.enhance_panel.status.setText(self.tr("wait_close_enhance"))
            event.ignore()
            return
        if self.id_photo_panel.worker is not None:
            self.id_photo_panel.status.setText(self.tr("wait_close_id_photo"))
            event.ignore()
            return
        if self.caj_panel.worker is not None:
            self.caj_panel.status.setText(self.tr("wait_close_caj"))
            event.ignore()
            return
        for panel in (self.pdf_panel, self.media_panel, self.compress_panel, self.enhance_panel, self.id_photo_panel, self.caj_panel):
            discard_staged_output(panel.output_path)
            panel.output_path = None
        super().closeEvent(event)

    def export(self) -> None:
        if not self.image: return
        path, _ = QFileDialog.getSaveFileName(self, self.tr("export_title"), self.tr("export_name"), self.tr("png_filter"))
        if path: self.image.save(path, "PNG"); self.status.setText(self.tr("saved").format(name=Path(path).name))


if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("eastsheng.NiuBToolbox")
        except (AttributeError, OSError):
            pass
    app = QApplication(sys.argv)
    app.setApplicationName("NiuB工具箱")
    app.setWindowIcon(QIcon(str(resource_path("assets/app-icon.ico"))))
    window = NiuBToolbox(); window.show()
    sys.exit(app.exec())
