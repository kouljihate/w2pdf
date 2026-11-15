"""Arabic → French translation module.

Uses the keyless free translation backends exposed by `deep-translator`:
MyMemory first (generous anonymous quota, reliable from shared IPs) with Google
as a fallback. Only texts containing Arabic are translated; anything else comes
back as an empty string so the PDF builder keeps the original wording.
"""

from __future__ import annotations

import re

from deep_translator import GoogleTranslator, MyMemoryTranslator

SOURCE_LANGUAGE = "ar"
TARGET_LANGUAGE = "fr"

# Characters per request. MyMemory rejects long queries, Google accepts ~5000.
PROVIDER_CHUNK_CHARS: dict[str, int] = {"mymemory": 400, "google": 4000}
PROVIDER_ORDER: tuple[str, ...] = ("mymemory", "google")

_ARABIC_RE = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]"
)
_MYMEMORY_WARNING = "MYMEMORY WARNING"


class TranslationError(RuntimeError):
    """Raised when no translation backend could translate a text."""


def contains_arabic(text: str) -> bool:
    """True when the text holds at least one Arabic-script character."""
    return bool(text) and bool(_ARABIC_RE.search(text))


def _split_chunks(text: str, limit: int) -> list[str]:
    """Split text into pieces a single request accepts, preferring line breaks."""
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    buffer = ""
    for line in text.split("\n"):
        while len(line) > limit:
            if buffer:
                chunks.append(buffer)
                buffer = ""
            cut = line.rfind(" ", 0, limit) or limit
            chunks.append(line[:cut])
            line = line[cut:].lstrip()
        candidate = f"{buffer}\n{line}" if buffer else line
        if len(candidate) > limit:
            chunks.append(buffer)
            buffer = line
        else:
            buffer = candidate
    if buffer:
        chunks.append(buffer)
    return [chunk for chunk in chunks if chunk.strip()]


def _make_translator(provider: str):
    if provider == "mymemory":
        return MyMemoryTranslator(source="ar-SA", target="fr-FR")
    if provider == "google":
        return GoogleTranslator(source=SOURCE_LANGUAGE, target=TARGET_LANGUAGE)
    raise ValueError(f"Unknown translation provider: {provider}")


def _translate_with(text: str, provider: str) -> str:
    limit = PROVIDER_CHUNK_CHARS[provider]
    translator = _make_translator(provider)
    parts: list[str] = []
    for chunk in _split_chunks(text, limit):
        translated = translator.translate(chunk)
        if not translated or _MYMEMORY_WARNING in translated.upper():
            raise RuntimeError("backend returned no usable translation")
        parts.append(translated.strip())
    return "\n".join(parts)


def translate_arabic_to_french(text: str, provider: str = "auto") -> str:
    """Translate one Arabic block into French.

    ``provider="auto"`` tries every backend in order. Returns an empty string
    when the block holds no Arabic; raises TranslationError when all backends fail.
    """
    text = (text or "").strip()
    if not text or not contains_arabic(text):
        return ""

    providers = PROVIDER_ORDER if provider == "auto" else (provider,)
    problems: list[str] = []
    for name in providers:
        try:
            return _translate_with(text, name)
        except Exception as exc:  # deep-translator raises plain exceptions
            problems.append(f"{name}: {exc}")

    raise TranslationError(
        "Arabic → French translation failed. Check the container's internet access "
        "and try again. Details — " + " | ".join(problems)
    )
