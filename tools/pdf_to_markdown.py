from __future__ import annotations

import re
import shutil
import tempfile
from hashlib import sha256
from pathlib import Path
from typing import Callable

import pymupdf
from markitdown._stream_info import StreamInfo
from markitdown.converters import PdfConverter


ProgressCallback = Callable[[str, int], None]


class PdfToMarkdownConverter:
    """Convert a PDF into Markdown plus locally referenced images."""

    def __init__(self, language: str = "zh") -> None:
        self.language = language

    @staticmethod
    def _safe_stem(path: Path) -> str:
        stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", path.stem).strip(" .")
        return stem or "Paper"

    @staticmethod
    def _unique_output(parent: Path, stem: str) -> Path:
        candidate = parent / f"{stem}_markdown"
        suffix = 2
        while candidate.exists():
            candidate = parent / f"{stem}_markdown_{suffix}"
            suffix += 1
        return candidate

    def _emit(self, callback: ProgressCallback | None, key: str, percent: int) -> None:
        if callback is not None:
            callback(key, percent)

    @staticmethod
    def _text_from_block(block: dict) -> str:
        lines: list[str] = []
        for line in block.get("lines", []):
            text = "".join(span.get("text", "") for span in line.get("spans", [])).strip()
            if text:
                lines.append(text)
        return "\n".join(lines)

    @staticmethod
    def _insert_figure(markdown: str, anchor: str, reference: str, start: int) -> tuple[str, int, bool]:
        """Insert a figure after nearby extracted text while preserving document order."""
        candidates = [line.strip() for line in reversed(anchor.splitlines()) if len(line.strip()) >= 4]
        for candidate in candidates:
            # A shorter tail is more tolerant of minor PDF extractor differences.
            for needle in (candidate, candidate[-80:], candidate[-40:]):
                position = markdown.find(needle, start)
                if position >= 0:
                    line_end = markdown.find("\n", position + len(needle))
                    if line_end < 0:
                        line_end = len(markdown)
                    insertion = f"\n\n{reference}\n"
                    markdown = markdown[:line_end] + insertion + markdown[line_end:]
                    return markdown, line_end + len(insertion), True
        return markdown, start, False

    def convert(self, pdf_path: str | Path, callback: ProgressCallback | None = None) -> Path:
        source = Path(pdf_path).resolve()
        if not source.is_file() or source.suffix.lower() != ".pdf":
            raise ValueError("Please select a valid PDF file.")

        stem = self._safe_stem(source)
        destination = self._unique_output(source.parent, stem)
        temp_root = Path(tempfile.mkdtemp(prefix=f".{stem}_markdown_", dir=source.parent))
        try:
            self._emit(callback, "extracting_text", 10)
            # Calling MarkItDown.convert_local() constructs Magika only to detect
            # the file type. The input is already validated as PDF, so invoke the
            # official PDF converter directly and avoid a separate Magika model.
            with source.open("rb") as pdf_stream:
                result = PdfConverter().convert(
                    pdf_stream,
                    StreamInfo(extension=".pdf", mimetype="application/pdf"),
                )
            markdown = getattr(result, "markdown", None) or getattr(result, "text_content", "")
            if not markdown.strip():
                raise RuntimeError("No readable text was found in this PDF.")

            figures_dir = temp_root / "images"
            figures_dir.mkdir()

            self._emit(callback, "extracting_images", 35)
            document = pymupdf.open(source)
            extracted: list[tuple[str, str]] = []
            seen_images: set[str] = set()
            figure_count = 0
            total_pages = max(1, document.page_count)

            for page_number, page in enumerate(document):
                previous_text = ""
                blocks = page.get_text("dict").get("blocks", [])
                blocks.sort(key=lambda block: (block.get("bbox", (0, 0, 0, 0))[1], block.get("bbox", (0, 0, 0, 0))[0]))
                for block in blocks:
                    if block.get("type") == 0:
                        text = self._text_from_block(block)
                        if text:
                            previous_text = text
                        continue
                    if block.get("type") != 1 or not block.get("image"):
                        continue
                    image_bytes = block["image"]
                    digest = sha256(image_bytes).hexdigest()
                    if digest in seen_images:
                        continue
                    seen_images.add(digest)
                    extension = str(block.get("ext", "png")).lower()
                    if not re.fullmatch(r"[a-z0-9]+", extension):
                        extension = "png"
                    figure_count += 1
                    image_path = figures_dir / f"figure_{figure_count:03d}.{extension}"
                    image_path.write_bytes(image_bytes)
                    extracted.append((f"![Figure {figure_count}](images/{image_path.name})", previous_text))

                self._emit(callback, "extracting_images", 35 + int(50 * (page_number + 1) / total_pages))
            document.close()

            figure_heading = "## 提取图片" if self.language == "zh" else "## Extracted Images"
            cursor = 0
            unplaced: list[str] = []
            if extracted:
                for reference, anchor in extracted:
                    markdown, cursor, placed = self._insert_figure(markdown, anchor, reference, cursor)
                    if not placed:
                        unplaced.append(reference)
            if unplaced:
                markdown = f"{markdown.rstrip()}\n\n{figure_heading}\n\n" + "\n\n".join(unplaced) + "\n"

            markdown_path = temp_root / f"{stem}.md"
            markdown_path.write_text(markdown.rstrip() + "\n", encoding="utf-8")
            self._emit(callback, "saving", 95)
            temp_root.rename(destination)
            self._emit(callback, "done", 100)
            return destination
        except Exception:
            shutil.rmtree(temp_root, ignore_errors=True)
            raise
