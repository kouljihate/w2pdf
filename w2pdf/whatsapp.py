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
    r"(?P<date>\d{1,4}[/.\-]\d{1,2}[/.\-]\d{1,4})[,\u060c\u066c]?\s+"
    r"(?P<time>\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap\u0635\u0645]\.?[Mm]?\.?)?)"
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


# Phones set to Arabic write timestamps with Arabic-Indic (٣) or Persian (۳) digits and
# may use a narrow no-break space before AM/PM. `strptime` accepts none of that, so the
# line matched while its date came back empty. Only timestamps are translated: the
# message text keeps the digits the sender actually typed.
_DIGIT_FIXES = str.maketrans(
    {
        **{arabic: latin for arabic, latin in zip("٠١٢٣٤٥٦٧٨٩", "0123456789")},
        **{persian: latin for persian, latin in zip("۰۱۲۳۴۵۶۷۸۹", "0123456789")},
        "\u060c": ",",
        "\u066c": ",",
        "\u066b": ".",
        "\u202f": " ",
        "\u00a0": " ",
    }
)

# Invisible marks WhatsApp wraps around lines; they are never part of the content.
_MARK_FIXES = str.maketrans(
    {mark: None for mark in "\u200e\u200f\u202a\u202b\u202c\u202d\u202e\ufeff"}
)


def _clean(line: str) -> str:
    """Drop the invisible marks WhatsApp leaves in a line."""
    return line.translate(_MARK_FIXES)


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
    date = date.translate(_DIGIT_FIXES)
    # Arabic locales mark the meridiem as ص (AM) or م (PM).
    time = time.translate(_DIGIT_FIXES).replace("ص", "AM").replace("م", "PM")
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
    return _parse_by_parts(date, time)


def _parse_by_parts(date: str, time: str) -> datetime | None:
    """Read a timestamp field by field, so a matched line never loses its date."""
    pieces = [piece.strip() for piece in re.split(r"[/.\-]", date) if piece.strip()]
    if len(pieces) != 3 or not all(piece.isdigit() for piece in pieces):
        return None
    numbers = [int(piece) for piece in pieces]
    if numbers[0] > 31:  # year first: 2026/11/05
        year, month, day = numbers
    else:
        first, second, year = numbers
        # A number above 12 can only be a day, so 1/14/26 is month-first (US phones)
        # while 14/1/26 and the ambiguous 5/11/26 stay day-first.
        if first <= 12 < second:
            month, day = first, second
        else:
            day, month = first, second
    if year < 100:
        year += 2000

    clock = re.match(
        r"^\s*(?P<hour>\d{1,2}):(?P<minute>\d{2})(?::(?P<second>\d{2}))?"
        r"\s*(?P<meridiem>[APap])?\.?[Mm]?\.?\s*$",
        time,
    )
    if not clock:
        return None
    hour = int(clock.group("hour"))
    minute = int(clock.group("minute"))
    second = int(clock.group("second") or 0)
    meridiem = (clock.group("meridiem") or "").upper()
    if meridiem == "P" and hour < 12:
        hour += 12
    elif meridiem == "A" and hour == 12:
        hour = 0
    try:
        return datetime(year, month, day, hour, minute, second)
    except ValueError:
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
    audios: set[str] | None = None,
) -> list[dict]:
    """Map messages to sequential document items.

    Photos are embedded as they are, videos are flagged so a still frame can be
    taken at build time, audio is listed as a voice message (a PDF cannot play
    it), plain text is translated later, and Facebook links are dropped. Numbers
    run in chat order, so every item keeps its place.
    """
    images = images or {}
    videos = videos or {}
    audios = audios or set()
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
                    "date_full": message.time_label,
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
                    "date_full": message.time_label,
                    "content": content,
                    "media": reference,
                    "caption": caption,
                    "text": "",
                    "data": b"",
                }
            )
            continue

        if key and key in audios:
            content = "Voice message"
            if caption:
                content += f" — {caption}"
            items.append(
                {
                    "include": True,
                    "seq": sequence,
                    "type": "Audio",
                    "sender": message.sender,
                    "date": message.short_label,
                    "date_full": message.time_label,
                    "content": content,
                    "media": reference,
                    "caption": caption,
                    "text": content,
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
                "date_full": message.time_label,
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
