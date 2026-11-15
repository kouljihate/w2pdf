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
        if self.timestamp is None:
            return ""
        return self.timestamp.strftime("%d/%m/%Y %H:%M")


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


def chat_items(messages: list[ChatMessage], images: dict[str, bytes] | None = None) -> list[dict]:
    """Map messages to sequential document items, pairing photos from the archive.

    Numbers run in chat order, so every photo keeps the place of the message that
    sent it and the texts that follow stay attached to it.
    """
    images = images or {}
    items: list[dict] = []
    sequence = 0
    for message in messages:
        sequence += 1
        reference = (message.media or "").strip()
        key = os.path.basename(reference.replace("\\", "/")).lower() if reference else ""
        payload = images.get(key) if key else None
        if payload is not None:
            content = reference
            if message.text:
                content += f" — {message.text}"
            items.append(
                {
                    "include": True,
                    "seq": sequence,
                    "type": "Photo",
                    "sender": message.sender,
                    "date": message.time_label,
                    "content": content,
                    "media": reference,
                    "caption": message.text,
                    "text": "",
                    "data": payload,
                }
            )
            continue

        text = message.text or (f"Attachment: {reference}" if reference else "")
        if not text.strip():
            continue
        items.append(
            {
                "include": True,
                "seq": sequence,
                "type": "Text",
                "sender": message.sender,
                "date": message.time_label,
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
