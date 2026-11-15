"""Assemble images and chat texts into a PDF.

Text layout is done on a raw ReportLab canvas so that Arabic lines can be shaped
(arabic-reshaper + python-bidi) and drawn right-to-left without relying on
ReportLab's limited RTL paragraph support.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from typing import Sequence

import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageOps
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, LEGAL, LETTER
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

from . import fonts

PAGE_SIZES: dict[str, tuple[float, float]] = {"A4": A4, "Letter": LETTER, "Legal": LEGAL}

TRANSLATION_MODE_LABELS: dict[str, str] = {
    "none": "Original only",
    "both": "Original + French",
    "translated": "French only",
}

INK = HexColor("#111827")
MUTED = HexColor("#6B7280")
RULE = HexColor("#D1D5DB")
FRENCH_INK = HexColor("#0B5F58")

_ARABIC_RE = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]"
)


class PdfExportError(RuntimeError):
    """Raised when the PDF cannot be produced (e.g. no Arabic font available)."""


@dataclass(slots=True)
class ImageBlock:
    """An image to place in the document."""

    name: str
    data: bytes
    caption: str = ""
    sequence: float = 0.0


@dataclass(slots=True)
class TextBlock:
    """A chat message or pasted paragraph, with its optional French translation."""

    text: str
    sender: str = ""
    timestamp: str = ""
    translation: str = ""
    sequence: float = 0.0


@dataclass(slots=True)
class PdfOptions:
    """User-facing document settings."""

    page_size: str = "A4"
    landscape: bool = False
    margin_mm: float = 15.0
    title: str = ""
    images_per_page: int = 1
    translation_mode: str = "none"
    show_metadata: bool = True
    page_numbers: bool = True
    max_image_px: int = 2200


def has_arabic(text: str) -> bool:
    """True when the text contains Arabic-script characters."""
    return bool(text) and bool(_ARABIC_RE.search(text))


def shape_arabic(text: str) -> str:
    """Reshape Arabic letters and apply the bidi algorithm for visual drawing."""
    return get_display(arabic_reshaper.reshape(text))


def _display(text: str) -> str:
    return shape_arabic(text) if has_arabic(text) else text


def _prepare_image(data: bytes, max_px: int) -> tuple[ImageReader, int, int] | None:
    """Load, orient, flatten and downscale an image for embedding."""
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
        img = ImageOps.exif_transpose(img)
        if img.mode in ("RGBA", "LA", "P"):
            flattened = Image.new("RGB", img.size, "white")
            rgba = img.convert("RGBA")
            flattened.paste(rgba, mask=rgba.split()[-1])
            img = flattened
        elif img.mode != "RGB":
            img = img.convert("RGB")
        if max_px and max(img.size) > max_px:
            img.thumbnail((max_px, max_px), Image.LANCZOS)
        return ImageReader(img), img.width, img.height
    except Exception:
        return None


class _Document:
    """Thin paging layer over a ReportLab canvas."""

    def __init__(self, buffer: io.BytesIO, options: PdfOptions, arabic_font: str | None):
        self.options = options
        width, height = PAGE_SIZES.get(options.page_size, A4)
        if options.landscape:
            width, height = height, width
        self.page_size = (width, height)
        self.arabic_font = arabic_font
        self.arabic_bold = fonts.arabic_bold() or arabic_font
        self.latin = fonts.latin_font()
        self.latin_bold = fonts.latin_bold()

        self.canvas = canvas.Canvas(buffer, pagesize=self.page_size, pageCompression=1)
        self.canvas.setTitle(options.title or "WhatsApp export")
        self.canvas.setAuthor("W2PDF")
        self.canvas.setSubject("WhatsApp images and messages")

        self.margin = max(6.0, min(40.0, float(options.margin_mm))) * mm
        self.left = self.margin
        self.right = width - self.margin
        self.width = self.right - self.left
        self.top = height - self.margin
        self.bottom = self.margin + (13 * mm if options.page_numbers else 0)

        self.y = self.top
        self.page_no = 0
        self.page_content = False
        self._new_page()

    # -- page handling ---------------------------------------------------
    def _new_page(self) -> None:
        if self.page_no:
            self.canvas.showPage()
        self.page_no += 1
        self.y = self.top
        self.page_content = False
        if self.options.page_numbers:
            self._draw_footer()

    @property
    def free_height(self) -> float:
        return self.y - self.bottom

    def force_new_page(self) -> None:
        """Start a new page unless the current one holds only the title."""
        if self.page_content:
            self._new_page()

    def _draw_footer(self) -> None:
        footer_y = self.margin * 0.5
        c = self.canvas
        c.saveState()
        c.setStrokeColor(RULE)
        c.setLineWidth(0.5)
        c.line(self.left, footer_y + 9, self.right, footer_y + 9)
        c.setFillColor(MUTED)
        label = self.options.title or "WhatsApp export"
        if has_arabic(label) and self.arabic_font:
            c.setFont(self.arabic_font, 8)
            c.drawString(self.left, footer_y, _display(label))
        else:
            c.setFont(self.latin, 8)
            c.drawString(self.left, footer_y, self._clip(label, self.latin, 8, self.width * 0.7))
        c.setFont(self.latin, 8)
        c.drawRightString(self.right, footer_y, f"Page {self.page_no}")
        c.restoreState()

    def close(self) -> None:
        self.canvas.showPage()
        self.canvas.save()

    # -- measuring -------------------------------------------------------
    @staticmethod
    def _clip(text: str, font: str, size: float, max_width: float) -> str:
        if pdfmetrics.stringWidth(text, font, size) <= max_width:
            return text
        clipped = text
        while clipped and pdfmetrics.stringWidth(clipped + "...", font, size) > max_width:
            clipped = clipped[:-1]
        return clipped + "..."

    @staticmethod
    def _width(text: str, font: str, size: float) -> float:
        return pdfmetrics.stringWidth(_display(text), font, size)

    def _wrap(self, text: str, font: str, size: float, width: float) -> list[str]:
        words = text.split()
        if not words:
            return [""]
        lines: list[str] = []
        current = ""
        for word in words:
            trial = f"{current} {word}" if current else word
            if self._width(trial, font, size) <= width:
                current = trial
                continue
            if current:
                lines.append(current)
                current = ""
            while word and self._width(word, font, size) > width:
                cut = len(word)
                while cut > 1 and self._width(word[:cut], font, size) > width:
                    cut -= 1
                lines.append(word[:cut])
                word = word[cut:]
            current = word
        if current:
            lines.append(current)
        return lines or [""]

    def _ensure(self, height: float) -> None:
        if self.free_height < height and self.page_content:
            self._new_page()

    def _advance(self, height: float) -> None:
        self.y -= height

    def advance(self, height: float) -> None:
        """Move the cursor down by a gap between blocks."""
        self._advance(height)

    # -- content ---------------------------------------------------------
    def title_block(self, title: str) -> None:
        title = title.strip()
        if not title:
            return
        size = 21
        font = self.arabic_bold if has_arabic(title) and self.arabic_bold else self.latin_bold
        direction_rtl = has_arabic(title)
        for line in self._wrap(title, font, size, self.width):
            self._advance(size * 1.2)
            self.canvas.setFont(font, size)
            self.canvas.setFillColor(INK)
            if direction_rtl:
                self.canvas.drawRightString(self.right, self.y + 4, _display(line))
            else:
                self.canvas.drawString(self.left, self.y + 4, line)
        self._advance(6)
        self.canvas.setStrokeColor(RULE)
        self.canvas.setLineWidth(0.8)
        self.canvas.line(self.left, self.y, self.right, self.y)
        self._advance(8)

    def draw_text(
        self,
        text: str,
        *,
        size: float = 10.5,
        color=INK,
        bold: bool = False,
        line_gap: float = 1.45,
        align: str = "auto",
    ) -> None:
        for raw_line in text.split("\n"):
            raw_line = raw_line.rstrip()
            if not raw_line.strip():
                self._advance(size * line_gap * 0.6)
                continue
            line_is_arabic = has_arabic(raw_line)
            if line_is_arabic and self.arabic_font:
                font = (self.arabic_bold or self.arabic_font) if bold else self.arabic_font
            else:
                font = self.latin_bold if bold else self.latin
            for piece in self._wrap(raw_line, font, size, self.width):
                line_height = size * line_gap
                self._ensure(line_height)
                self._advance(line_height)
                baseline = self.y + line_height * 0.22
                self.canvas.setFont(font, size)
                self.canvas.setFillColor(color)
                if line_is_arabic:
                    self.canvas.drawRightString(self.right, baseline, _display(piece))
                elif align == "center":
                    self.canvas.drawCentredString(self.left + self.width / 2, baseline, piece)
                else:
                    self.canvas.drawString(self.left, baseline, piece)
                self.page_content = True

    def add_message(self, block: TextBlock, mode: str, show_metadata: bool) -> None:
        parts: list[str] = []
        if mode in ("none", "both"):
            parts.append(block.text)
        if block.translation and mode in ("both", "translated"):
            parts.append(block.translation)
        if not parts:
            parts.append(block.text)

        if show_metadata:
            meta = " | ".join(p for p in (block.sender, block.timestamp) if p)
            if meta:
                self.draw_text(meta, size=8, color=MUTED, bold=True, line_gap=1.5)

        show_label = mode == "both" and bool(block.translation)
        for index, body in enumerate(parts):
            if index == 1 and show_label:
                self._advance(2)
                self.draw_text("FR", size=7, color=FRENCH_INK, bold=True, line_gap=1.3)
            is_translation = index == 1 and bool(block.translation)
            self.draw_text(body, size=10.5, color=FRENCH_INK if is_translation else INK)
        self._advance(9)

    def add_image(self, block: ImageBlock, slot_height: float) -> None:
        prepared = _prepare_image(block.data, self.options.max_image_px)
        if prepared is None:
            self.draw_text(f"[Unreadable image: {block.name}]", size=9, color=MUTED)
            return

        caption_lines: list[str] = []
        caption_height = 0.0
        caption = block.caption.strip()
        caption_font = (
            self.arabic_font if has_arabic(caption) and self.arabic_font else self.latin
        )
        if caption:
            caption_lines = self._wrap(caption, caption_font, 9, self.width * 0.9)
            caption_height = len(caption_lines) * 9 * 1.5 + 8

        reader, img_w, img_h = prepared
        available_h = max(slot_height - caption_height, 30)
        scale = min(self.width / img_w, available_h / img_h)
        draw_w, draw_h = img_w * scale, img_h * scale
        x = self.left + (self.width - draw_w) / 2

        top = self.y
        self.canvas.drawImage(reader, x, top - draw_h, draw_w, draw_h, mask=None)
        self.page_content = True
        self.y = top - draw_h

        if caption_lines:
            self._advance(8)
            line_height = 9 * 1.5
            for line in caption_lines:
                self._ensure(line_height)
                self._advance(line_height)
                self.canvas.setFont(caption_font, 9)
                self.canvas.setFillColor(MUTED)
                self.canvas.drawCentredString(
                    self.left + self.width / 2, self.y + line_height * 0.2, _display(line)
                )


# How much of the free page height a photo may use when its texts follow it.
PHOTO_SHARE_WITH_TEXT = 0.62


def order_blocks(blocks: Sequence[ImageBlock | TextBlock]) -> list[ImageBlock | TextBlock]:
    """Sort images and texts by their sequence; at equal numbers photos come first."""
    return sorted(
        blocks,
        key=lambda block: (block.sequence, 0 if isinstance(block, ImageBlock) else 1),
    )


def build_pdf(
    blocks: Sequence[ImageBlock | TextBlock],
    options: PdfOptions,
) -> bytes:
    """Render the sequenced images and texts into a PDF and return its bytes."""
    ordered = order_blocks(blocks)
    needs_arabic = any(
        (has_arabic(item.caption) or has_arabic(item.name))
        if isinstance(item, ImageBlock)
        else (has_arabic(item.text) or has_arabic(item.translation))
        for item in ordered
    )
    arabic_font = fonts.arabic_font()
    if needs_arabic and arabic_font is None:
        raise PdfExportError(
            "No Arabic-capable font is installed, so the Arabic text cannot be rendered. "
            "The image ships VIP Rawy in static/fonts; install fonts-hosny-amiri or "
            "fonts-noto-core when running outside Docker."
        )

    buffer = io.BytesIO()
    doc = _Document(buffer, options, arabic_font)
    doc.title_block(options.title)

    per_page = 2 if options.images_per_page == 2 else 1
    gap = 10
    index = 0
    while index < len(ordered):
        item = ordered[index]
        if isinstance(item, TextBlock):
            doc.add_message(item, options.translation_mode, options.show_metadata)
            index += 1
            continue

        # Consecutive photos (nothing between them) share a gallery page.
        run: list[ImageBlock] = [item]
        cursor = index + 1
        while per_page > 1 and cursor < len(ordered) and len(run) < per_page:
            following = ordered[cursor]
            if not isinstance(following, ImageBlock):
                break
            run.append(following)
            cursor += 1

        doc.force_new_page()
        if len(run) > 1:
            slot = (doc.free_height - gap * (len(run) - 1)) / len(run)
            for block in run:
                doc.add_image(block, slot)
                doc.advance(gap)
            index = cursor
            continue

        followed_by_text = cursor < len(ordered) and isinstance(ordered[cursor], TextBlock)
        slot = doc.free_height * PHOTO_SHARE_WITH_TEXT if followed_by_text else doc.free_height
        doc.add_image(item, slot)
        index += 1

    doc.close()
    return buffer.getvalue()
