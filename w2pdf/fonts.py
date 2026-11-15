"""Arabic-capable font discovery for ReportLab.

ReportLab's built-in Type 1 fonts cannot draw Arabic, so an embedded TrueType
font with Arabic glyphs is required. The Docker image installs Amiri and Noto
Naskh Arabic; when running outside Docker a system font is used instead.
"""

from __future__ import annotations

import os
from functools import lru_cache

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_ALIAS = "W2PDF-Arabic"
FONT_REGULAR_ALIAS = "W2PDF-Arabic"

_HERE = os.path.dirname(os.path.abspath(__file__))

# Known-good paths first, in order of preference.
_CANDIDATES: tuple[str, ...] = (
    os.path.join(_HERE, os.pardir, "assets", "fonts", "Amiri-Regular.ttf"),
    "/usr/share/fonts/truetype/hosny-amiri/Amiri-Regular.ttf",
    "/usr/share/fonts/truetype/amiri/Amiri-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoNaskhArabicUI-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
    "/usr/share/fonts/opentype/noto/NotoNaskhArabic-Regular.ttf",
    "/usr/share/fonts/truetype/kacst/KacstOne.ttf",
    # Windows (local development)
    "C:/Windows/Fonts/arabtype.ttf",
    "C:/Windows/Fonts/tahoma.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    # macOS (local development)
    "/System/Library/Fonts/Supplemental/Al Nile.ttf",
    "/System/Library/Fonts/Supplemental/Geeza Pro.ttf",
)


@lru_cache(maxsize=1)
def arabic_font() -> str | None:
    """Register and return the ReportLab font name, or None when unavailable."""
    if FONT_ALIAS in pdfmetrics.getRegisteredFontNames():
        return FONT_ALIAS
    for path in _CANDIDATES:
        if not os.path.isfile(path):
            continue
        try:
            pdfmetrics.registerFont(TTFont(FONT_ALIAS, path))
        except Exception:
            continue
        return FONT_ALIAS
    return None


def arabic_font_available() -> bool:
    """True when Arabic text can be rendered into the PDF."""
    return arabic_font() is not None
