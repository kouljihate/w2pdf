"""Font registration for the PDF.

Comfortaa carries Latin/French text and VIP Rawy carries Arabic; both ship in
`static/fonts` (copied into the image). If a bundled font is missing, the
project falls back to system Arabic fonts and finally to ReportLab's built-in
Helvetica for Latin text.
"""

from __future__ import annotations

import os
from functools import lru_cache

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_FONT_DIRS = (
    os.path.join(_ROOT, "static", "fonts"),
    os.path.join(os.getcwd(), "static", "fonts"),
)

LATIN_REGULAR = "W2PDF-Latin"
LATIN_BOLD = "W2PDF-Latin-Bold"
ARABIC_REGULAR = "W2PDF-Arabic"
ARABIC_BOLD = "W2PDF-Arabic-Bold"

# System fallbacks, used when the bundled fonts are absent.
_SYSTEM_ARABIC = (
    "/usr/share/fonts/truetype/hosny-amiri/Amiri-Regular.ttf",
    "/usr/share/fonts/truetype/amiri/Amiri-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
    "/usr/share/fonts/opentype/noto/NotoNaskhArabic-Regular.ttf",
    "/usr/share/fonts/truetype/kacst/KacstOne.ttf",
    "C:/Windows/Fonts/arabtype.ttf",
    "C:/Windows/Fonts/tahoma.ttf",
    "/System/Library/Fonts/Supplemental/Al Nile.ttf",
)

_SYSTEM_ARABIC_BOLD = (
    "/usr/share/fonts/truetype/hosny-amiri/Amiri-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
    "/usr/share/fonts/opentype/noto/NotoNaskhArabic-Bold.ttf",
    "C:/Windows/Fonts/tahomabd.ttf",
    "/System/Library/Fonts/Supplemental/Al Nile Bold.ttf",
)


def _bundled(*names: str) -> list[str]:
    return [os.path.join(directory, name) for name in names for directory in _FONT_DIRS]


@lru_cache(maxsize=None)
def _register(alias: str, paths: tuple[str, ...]) -> str | None:
    """Register the first readable font, returning its ReportLab name."""
    if alias in pdfmetrics.getRegisteredFontNames():
        return alias
    for path in paths:
        if not os.path.isfile(path):
            continue
        try:
            pdfmetrics.registerFont(TTFont(alias, path))
        except Exception:
            continue
        return alias
    return None


@lru_cache(maxsize=1)
def latin_font() -> str:
    """Comfortaa for Latin text, or Helvetica when it is not available."""
    return (
        _register(
            LATIN_REGULAR,
            tuple(_bundled("Comfortaa-Regular.ttf", "Comfortaa-Light.ttf")),
        )
        or "Helvetica"
    )


@lru_cache(maxsize=1)
def latin_bold() -> str:
    """Comfortaa Bold, or Helvetica-Bold when it is not available."""
    return _register(LATIN_BOLD, tuple(_bundled("Comfortaa-Bold.ttf"))) or "Helvetica-Bold"


@lru_cache(maxsize=1)
def arabic_font() -> str | None:
    """VIP Rawy (or a system Arabic font), or None when no Arabic font exists."""
    return _register(ARABIC_REGULAR, tuple(_bundled("VIP-Rawy-Regular.ttf") + list(_SYSTEM_ARABIC)))


@lru_cache(maxsize=1)
def arabic_bold() -> str | None:
    """VIP Rawy Bold when available, otherwise the regular Arabic face."""
    return _register(ARABIC_BOLD, tuple(_bundled("VIP-Rawy-Bold.ttf") + list(_SYSTEM_ARABIC_BOLD))) or arabic_font()


def arabic_font_available() -> bool:
    """True when Arabic text can be rendered into the PDF."""
    return arabic_font() is not None
