from __future__ import annotations

import html
import hashlib
import io
import re
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table as DocxTable
from docx.text.paragraph import Paragraph as DocxParagraph
from PIL import Image as PillowImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _blocks(document):
    for child in document.element.body.iterchildren():
        if child.tag == qn("w:p"):
            yield DocxParagraph(child, document)
        elif child.tag == qn("w:tbl"):
            yield DocxTable(child, document)


class WindowsFontResolver:
    """Resolve Word font names to installed font files and embed them in PDFs."""

    FONT_ALIASES = {
        "微软雅黑": "Microsoft YaHei", "微软雅黑light": "Microsoft YaHei Light",
        "宋体": "SimSun", "新宋体": "NSimSun", "黑体": "SimHei",
        "楷体": "KaiTi", "楷体gb2312": "KaiTi", "仿宋": "FangSong",
        "仿宋gb2312": "FangSong", "等线": "DengXian",
    }

    def __init__(self, fallback: str) -> None:
        self.fallback = fallback
        self.fonts: list[tuple[str, Path]] = []
        self.registered: dict[Path, str] = {}
        self._load_registry_fonts()

    @staticmethod
    def _normalize(name: str) -> str:
        return re.sub(r"[^0-9a-z\u3400-\u9fff]", "", name.lower().replace("truetype", ""))

    def _load_registry_fonts(self) -> None:
        try:
            import winreg
            font_dir = Path("C:/Windows/Fonts")
            locations = (
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"),
            )
            for hive, key_name in locations:
                try:
                    with winreg.OpenKey(hive, key_name) as key:
                        for index in range(winreg.QueryInfoKey(key)[1]):
                            display, filename, _ = winreg.EnumValue(key, index)
                            if not isinstance(filename, str):
                                continue
                            path = Path(filename)
                            if not path.is_absolute(): path = font_dir / path
                            if not path.is_file() or path.suffix.lower() not in (".ttf", ".ttc", ".otf"): continue
                            clean_display = re.sub(r"\s*\([^)]*\)\s*$", "", display)
                            for alias in re.split(r"\s*&\s*", clean_display):
                                self.fonts.append((alias, path))
                except OSError:
                    continue
        except (ImportError, OSError):
            pass

    def resolve(self, requested: str | None, bold: bool = False, italic: bool = False) -> str:
        if not requested:
            return self.fallback
        requested = self.FONT_ALIASES.get(requested.lower().replace(" ", ""), requested)
        target = self._normalize(requested)
        candidates = []
        for display, path in self.fonts:
            normalized = self._normalize(display)
            if normalized == target or normalized.startswith(target):
                style_score = (10 if bold and "bold" in display.lower() else 0) + (8 if italic and ("italic" in display.lower() or "oblique" in display.lower()) else 0)
                exact_score = 4 if normalized == target else 0
                candidates.append((exact_score + style_score, path))
        if not candidates:
            return self.fallback
        path = max(candidates, key=lambda item: item[0])[1]
        if path in self.registered:
            return self.registered[path]
        font_name = f"NiuBFont_{hashlib.sha1(str(path).encode('utf-8')).hexdigest()[:12]}"
        try:
            pdfmetrics.registerFont(TTFont(font_name, str(path), subfontIndex=0))
            pdfmetrics.registerFontFamily(font_name, normal=font_name, bold=font_name, italic=font_name, boldItalic=font_name)
            self.registered[path] = font_name
            return font_name
        except Exception:
            return self.fallback


class DocxPdfRenderer:
    """Portable DOCX renderer for common paragraphs, tables, and inline images."""

    def __init__(self) -> None:
        self.font_name = "NiuBDocumentFont"
        for font_path in (Path("C:/Windows/Fonts/msyh.ttc"), Path("C:/Windows/Fonts/simsun.ttc"), Path("C:/Windows/Fonts/arial.ttf")):
            if not font_path.is_file():
                continue
            try:
                pdfmetrics.registerFont(TTFont(self.font_name, str(font_path), subfontIndex=0))
                pdfmetrics.registerFontFamily(self.font_name, normal=self.font_name, bold=self.font_name, italic=self.font_name, boldItalic=self.font_name)
                break
            except Exception:
                continue
        else:
            try:
                pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
                self.font_name = "STSong-Light"
            except Exception:
                self.font_name = "Helvetica"
        self.fonts = WindowsFontResolver(self.font_name)

    @staticmethod
    def _alignment(value) -> int:
        return {1: TA_CENTER, 2: TA_RIGHT, 3: TA_JUSTIFY}.get(value, TA_LEFT)

    def _paragraph_style(self, paragraph: DocxParagraph) -> ParagraphStyle:
        fmt = paragraph.paragraph_format
        size = paragraph.style.font.size.pt if paragraph.style and paragraph.style.font.size else 10.5
        for run in paragraph.runs:
            if run.font.size:
                size = max(6.0, min(48.0, run.font.size.pt))
                break
        return ParagraphStyle(
            "DocxParagraph", fontName=self.font_name, fontSize=size,
            leading=max(size * 1.35, 14), alignment=self._alignment(paragraph.alignment),
            spaceBefore=fmt.space_before.pt if fmt.space_before else 0,
            spaceAfter=fmt.space_after.pt if fmt.space_after else 5,
            leftIndent=fmt.left_indent.pt if fmt.left_indent else 0,
            rightIndent=fmt.right_indent.pt if fmt.right_indent else 0,
            firstLineIndent=fmt.first_line_indent.pt if fmt.first_line_indent else 0,
        )

    @staticmethod
    def _run_font_name(run, paragraph: DocxParagraph) -> str | None:
        r_fonts = run._r.get_or_add_rPr().rFonts
        east_asia = r_fonts.get(qn("w:eastAsia")) if r_fonts is not None else None
        ascii_name = run.font.name
        contains_cjk = bool(re.search(r"[\u3400-\u9fff]", run.text))
        style_name = paragraph.style.font.name if paragraph.style else None
        return east_asia if contains_cjk and east_asia else ascii_name or east_asia or style_name

    def _paragraph_markup(self, paragraph: DocxParagraph) -> str:
        parts: list[str] = []
        for run in paragraph.runs:
            text = html.escape(run.text).replace("\n", "<br/>")
            if not text:
                continue
            style_font = paragraph.style.font if paragraph.style else None
            bold = run.bold if run.bold is not None else bool(style_font and style_font.bold)
            italic = run.italic if run.italic is not None else bool(style_font and style_font.italic)
            underline = run.underline if run.underline is not None else bool(style_font and style_font.underline)
            font_name = self.fonts.resolve(self._run_font_name(run, paragraph), bold, italic)
            size = run.font.size.pt if run.font.size else (style_font.size.pt if style_font and style_font.size else None)
            color = str(run.font.color.rgb) if run.font.color and run.font.color.rgb else None
            attributes = [f'name="{font_name}"']
            if size: attributes.append(f'size="{max(6.0, min(72.0, size)):.2f}"')
            if color: attributes.append(f'color="#{color}"')
            text = f"<font {' '.join(attributes)}>{text}</font>"
            if bold: text = f"<b>{text}</b>"
            if italic: text = f"<i>{text}</i>"
            if underline: text = f"<u>{text}</u>"
            parts.append(text)
        return "".join(parts) or " "

    @staticmethod
    def _image_bytes(blob: bytes, quality: str) -> bytes:
        if quality != "small":
            return blob
        try:
            with PillowImage.open(io.BytesIO(blob)) as picture:
                picture.load()
                picture.thumbnail((1600, 1600), PillowImage.Resampling.LANCZOS)
                if picture.mode not in ("RGB", "L"):
                    background = PillowImage.new("RGB", picture.size, "white")
                    if "A" in picture.getbands(): background.paste(picture, mask=picture.getchannel("A"))
                    else: background.paste(picture)
                    picture = background
                output = io.BytesIO()
                picture.save(output, "JPEG", quality=72, optimize=True)
                compressed = output.getvalue()
                return compressed if len(compressed) < len(blob) else blob
        except Exception:
            return blob

    def _paragraph_images(self, paragraph: DocxParagraph, max_width: float, quality: str):
        images = []
        for drawing in paragraph._p.xpath(".//w:drawing"):
            blips = drawing.xpath(".//a:blip")
            if not blips:
                continue
            relation_id = blips[0].get(qn("r:embed"))
            if not relation_id or relation_id not in paragraph.part.related_parts:
                continue
            blob = self._image_bytes(paragraph.part.related_parts[relation_id].blob, quality)
            try:
                reader = ImageReader(io.BytesIO(blob)); width, height = reader.getSize()
                scale = min(1.0, max_width / width)
                images.extend((Image(io.BytesIO(blob), width=width * scale, height=height * scale), Spacer(1, 5)))
            except Exception:
                continue
        return images

    def convert(self, source: Path, destination: Path, quality: str) -> None:
        document = Document(str(source))
        section = document.sections[0]
        page_size = (section.page_width.pt, section.page_height.pt)
        margins = tuple(value.pt for value in (section.left_margin, section.right_margin, section.top_margin, section.bottom_margin))
        pdf = SimpleDocTemplate(
            str(destination), pagesize=page_size,
            leftMargin=margins[0], rightMargin=margins[1], topMargin=margins[2], bottomMargin=margins[3],
            pageCompression=1, title=source.stem,
        )
        available_width = page_size[0] - margins[0] - margins[1]
        story = []
        body_style = ParagraphStyle("TableCell", parent=getSampleStyleSheet()["BodyText"], fontName=self.font_name, fontSize=9, leading=12)
        for block in _blocks(document):
            if isinstance(block, DocxParagraph):
                story.append(Paragraph(self._paragraph_markup(block), self._paragraph_style(block)))
                story.extend(self._paragraph_images(block, available_width, quality))
            else:
                rows = [[[Paragraph(self._paragraph_markup(paragraph), self._paragraph_style(paragraph)) for paragraph in cell.paragraphs] for cell in row.cells] for row in block.rows]
                if rows and rows[0]:
                    table = Table(rows, colWidths=[available_width / len(rows[0])] * len(rows[0]), repeatRows=1)
                    table.setStyle(TableStyle([
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#b8b8b8")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ]))
                    story.extend((table, Spacer(1, 7)))
        pdf.build(story or [Paragraph(" ", body_style)])
