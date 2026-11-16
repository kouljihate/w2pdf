"""Parse WhatsApp "Export chat" .txt files into structured messages."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime

# Matches both export flavours:
#   [15/11/2026, 08:35:12] Alice: Bonjour
#   15/11/2026, 08:35 - Alice: مرحبا
_LINE_RE = re.compile(
    r"^\[?"
    r"(?P<date>\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}),?\s+"
    r"(?P<time>\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap]\.?[Mm]\.?)?)"
    r"\]?\s*(?:[-–—]\s*)?"
    r"(?P<sender>[^:\n]{1,80}?):\s?"
    r"(?P<body>.*)$"
)

_DATE_FORMATS = ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%y %H:%M:%S", "%d/%m/%y %H:%M")

# Attachment references inside exports that include media:
#   iOS      <attached: 00000042-PHOTO-2024-03-12-21-04-11.jpg>
#   Android  IMG-20240315-WA0001.jpg (file attached)
_ATTACHED_RE = re.compile(r"<attached:\s*(?P<name>[^>]+)>", re.IGNORECASE)
_FILE_ATTACHED_RE = re.compile(
    r"^(?P<name>[^\n]+?\.(?P<ext>[A-Za-z0-9]{2,5}))\s*\(file attached\)", re.IGNORECASE
)

# Facebook links are dropped from the document entirely.
_FACEBOOK_RE = re.compile(
    r"(?:https?://)?(?:[a-z0-9-]+\.)*(?:facebook\.com|fb\.watch|fb\.me|fb\.com)\S*",
    re.IGNORECASE,
)

# Lines WhatsApp itself inserts; not worth putting in a document.
_SYSTEM_HINTS = (
    "omitted",
    "end-to-end encrypted",
    "changed the subject",
    "changed this group's icon",
    "changed the group description",
    "created this group",
    "created group",
    "added you",
    "joined using this group's invite link",
    "changed their phone number",
    "this message was deleted",
    "you deleted this message",
    "started a call",
    "missed voice call",
    "missed video call",
    "messages and calls are",
)


@dataclass(slots=True)
class ChatMessage:
    """One message of an exported conversation."""

    sender: str
    text: str
    timestamp: datetime | None = None
    media: str | None = None

    @property
    def time_label(self) -> str:
        """Full date for the PDF header."""
        if self.timestamp is None:
            return ""
        return self.timestamp.strftime("%d/%m/%Y %H:%M")

    @property
    def short_label(self) -> str:
        """Compact date for the item table, matching the export's `d/m/yy, HH:MM`."""
        if self.timestamp is None:
            return ""
        return self.timestamp.strftime("%d/%m/%y %H:%M")


def decode_export(data: bytes) -> str:
    """Decode an exported chat file, which WhatsApp writes as UTF-8."""
    for encoding in ("utf-8-sig", "utf-16", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _clean(line: str) -> str:
    # WhatsApp wraps lines with LTR/RTL marks for display.
    return line.replace("\u200e", "").replace("\u200f", "").replace("\ufeff", "")


def _is_system(text: str) -> bool:
    lowered = text.lower()
    return not lowered.strip() or any(hint in lowered for hint in _SYSTEM_HINTS)


def _extract_attachment(body: str) -> tuple[str | None, str]:
    """Split an attachment reference from the caption that follows it."""
    match = _ATTACHED_RE.search(body)
    if match:
        return match.group("name").strip(), body.replace(match.group(0), "").strip()
    match = _FILE_ATTACHED_RE.match(body)
    if match:
        return match.group("name").strip(), body[match.end() :].strip()
    return None, body.strip()


def _parse_timestamp(date: str, time: str) -> datetime | None:
    stamp = f"{date} {time}".replace(".", "/").replace("-", "/")
    stamp = re.sub(r"\s*([APap])\.?[Mm]\.?$", r" \1M", stamp)
    stamp = stamp.replace("a.m.", "AM").replace("p.m.", "PM")
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(stamp, fmt)
        except ValueError:
            continue
    for fmt in ("%d/%m/%Y %I:%M:%S %p", "%d/%m/%Y %I:%M %p"):
        try:
            return datetime.strptime(stamp, fmt)
        except ValueError:
            continue
    return None


def parse_chat(raw: str) -> list[ChatMessage]:
    """Turn the raw text of a WhatsApp export into messages, in file order."""
    messages: list[ChatMessage] = []
    for raw_line in raw.splitlines():
        line = _clean(raw_line)
        match = _LINE_RE.match(line)
        if match:
            body = match.group("body").strip()
            if _is_system(body):
                continue
            messages.append(
                ChatMessage(
                    sender=match.group("sender").strip(),
                    text=body,
                    timestamp=_parse_timestamp(match.group("date"), match.group("time")),
                )
            )
        elif messages and line.strip() and not _is_system(line):
            # A wrapped continuation of the previous message.
            messages[-1].text = f"{messages[-1].text}\n{line.strip()}".strip()

    for message in messages:
        media, caption = _extract_attachment(message.text)
        message.media = media
        message.text = caption
    return messages


def strip_facebook_links(text: str) -> str:
    """Remove Facebook links; a message that was only a link ends up empty."""
    return re.sub(r"\s{2,}", " ", _FACEBOOK_RE.sub(" ", text or "")).strip()


def chat_items(
    messages: list[ChatMessage],
    images: dict[str, bytes] | None = None,
    videos: dict[str, bytes] | None = None,
) -> list[dict]:
    """Map messages to sequential document items.

    Photos are embedded as they are, videos are flagged so a still frame can be
    taken at build time, plain text is translated later, and Facebook links are
    dropped. Numbers run in chat order, so every item keeps its place.
    """
    images = images or {}
    videos = videos or {}
    items: list[dict] = []

    for message in messages:
        reference = (message.media or "").strip()
        key = os.path.basename(reference.replace("\\", "/")).lower() if reference else ""
        caption = strip_facebook_links(message.text or "")
        sequence = len(items) + 1

        if key and key in images:
            content = reference
            if caption:
                content += f" — {caption}"
            items.append(
                {
                    "include": True,
                    "seq": sequence,
                    "type": "Photo",
                    "sender": message.sender,
                    "date": message.short_label,
                    "content": content,
                    "media": reference,
                    "caption": caption,
                    "text": "",
                    "data": images[key],
                }
            )
            continue

        if key and key in videos:
            content = reference
            if caption:
                content += f" — {caption}"
            items.append(
                {
                    "include": True,
                    "seq": sequence,
                    "type": "Video",
                    "sender": message.sender,
                    "date": message.short_label,
                    "content": content,
                    "media": reference,
                    "caption": caption,
                    "text": "",
                    "data": b"",
                }
            )
            continue

        text = caption or (f"Attachment: {reference}" if reference else "")
        if not text.strip():
            continue  # Facebook link, or nothing left to print
        items.append(
            {
                "include": True,
                "seq": sequence,
                "type": "Text",
                "sender": message.sender,
                "date": message.short_label,
                "content": " ".join(text.split())[:120],
                "media": "",
                "caption": "",
                "text": text,
                "data": b"",
            }
        )
    return items


def split_paragraphs(raw: str) -> list[str]:
    """Split pasted text into blocks on blank lines."""
    blocks = [block.strip() for block in re.split(r"\n\s*\n", raw or "")]
    return [block for block in blocks if block]
