"""Read a WhatsApp chat export that includes media (the .zip archive).

WhatsApp writes either a bare .txt (without media) or a .zip holding a chat log
plus the attachments. The archive is read entirely in memory: no extraction to
disk, no path traversal outside the archive.
"""

from __future__ import annotations

import hashlib
import io
import os
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from .whatsapp import ChatMessage, decode_export, parse_chat

FILES_DIR_ENV = "W2PDF_FILES_DIR"
FILES_MARKER = ".w2pdf-archive"


def files_directory() -> Path:
    """Folder the archive's attachments are copied into."""
    return Path(os.environ.get(FILES_DIR_ENV, "files"))


def _clear_directory(directory: Path) -> None:
    """Empty a folder without touching anything outside it."""
    for entry in directory.iterdir():
        try:
            if entry.is_symlink() or not entry.is_dir():
                entry.unlink()
            else:
                shutil.rmtree(entry)
        except OSError:
            continue


def store_media_files(
    archive: zipfile.ZipFile,
    infos: list[zipfile.ZipInfo],
    marker: str,
    directory: Path,
) -> int:
    """Copy every non-.txt member into `directory`, clearing it first.

    The folder is emptied before a different archive is written, so leftovers from
    a previous export never mix with the current one. Re-reading the same archive
    is a no-op, which keeps Streamlit reruns cheap.
    """
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError:
        return -1

    marker_path = directory / FILES_MARKER
    try:
        if marker_path.read_text(encoding="utf-8").strip() == marker:
            return 0
    except OSError:
        pass

    _clear_directory(directory)
    written = 0
    for info in infos:
        if _is_unsafe(info.filename):
            continue
        name = os.path.basename(info.filename.replace("\\", "/"))
        if not name or name.lower().endswith(".txt"):
            continue
        try:
            (directory / name).write_bytes(archive.read(info.filename))
        except (OSError, zipfile.BadZipFile, RuntimeError):
            continue
        written += 1

    try:
        marker_path.write_text(marker + "\n", encoding="utf-8")
    except OSError:
        pass
    return written

IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"})
VIDEO_EXTENSIONS = frozenset({".mp4", ".3gp", ".mov", ".webm", ".mkv", ".avi", ".m4v"})
# Voice notes arrive as Opus; the rest are other audio WhatsApp can export.
AUDIO_EXTENSIONS = frozenset({".opus", ".ogg", ".oga", ".mp3", ".m4a", ".aac", ".wav", ".amr"})

MAX_ARCHIVE_BYTES = 400 * 1024 * 1024
MAX_IMAGE_BYTES = 30 * 1024 * 1024
# Videos are held only until their frame is extracted at build time.
MAX_VIDEO_FILE_BYTES = 60 * 1024 * 1024
MAX_VIDEO_TOTAL_BYTES = 200 * 1024 * 1024
# Voice notes stay in memory so they can be played in the preview list.
MAX_AUDIO_FILE_BYTES = 25 * 1024 * 1024
MAX_AUDIO_TOTAL_BYTES = 100 * 1024 * 1024


class ArchiveError(RuntimeError):
    """Raised when a .zip export cannot be read."""


@dataclass(slots=True)
class ChatExport:
    """Parsed chat log plus the images found in the same archive."""

    messages: list[ChatMessage] = field(default_factory=list)
    images: dict[str, bytes] = field(default_factory=dict)
    videos: dict[str, bytes] = field(default_factory=dict)
    # Audio never enters the PDF, but it is kept so the preview can play it.
    audios: dict[str, bytes] = field(default_factory=dict)
    chat_name: str = ""
    files_dir: str = ""
    stored_files: int = 0

    def image_for(self, reference: str | None) -> bytes | None:
        """Return the image bytes referenced by a chat line, if the archive has it."""
        if not reference:
            return None
        key = os.path.basename(reference.replace("\\", "/")).lower()
        return self.images.get(key)

    def video_for(self, reference: str | None) -> bytes | None:
        """Return the video bytes referenced by a chat line, if the archive has it."""
        if not reference:
            return None
        key = os.path.basename(reference.replace("\\", "/")).lower()
        return self.videos.get(key)

    def audio_for(self, reference: str | None) -> bytes | None:
        """Return the audio bytes referenced by a chat line, if the archive has it."""
        if not reference:
            return None
        key = os.path.basename(reference.replace("\\", "/")).lower()
        return self.audios.get(key)


def _is_unsafe(name: str) -> bool:
    normalised = name.replace("\\", "/")
    return normalised.startswith("/") or ".." in normalised.split("/")


def _pick_chat_log(names: list[str]) -> int:
    """Choose the chat log among the archive's .txt files."""
    def rank(name: str) -> tuple[int, str]:
        base = os.path.basename(name).lower()
        if base.startswith("_chat"):
            return (0, base)
        if "whatsapp chat" in base:
            return (1, base)
        return (2, base)

    return min(range(len(names)), key=lambda index: rank(names[index]))


def load_chat_archive(data: bytes) -> ChatExport:
    """Parse a WhatsApp .zip export into messages and their images."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise ArchiveError(
            "That file is not a readable .zip archive. Export the chat with media and "
            "upload the .zip unchanged."
        ) from exc

    text_names: list[str] = []
    image_names: list[str] = []
    video_names: list[str] = []
    audio_names: list[str] = []
    with archive:
        infos = [info for info in archive.infolist() if not info.is_dir()]
        for info in infos:
            if _is_unsafe(info.filename):
                continue
            base = os.path.basename(info.filename.replace("\\", "/"))
            lower = base.lower()
            extension = os.path.splitext(lower)[1]
            if lower.endswith(".txt"):
                text_names.append(info.filename)
            elif extension in IMAGE_EXTENSIONS:
                if info.file_size <= MAX_IMAGE_BYTES:
                    image_names.append(info.filename)
            elif extension in VIDEO_EXTENSIONS:
                if info.file_size <= MAX_VIDEO_FILE_BYTES:
                    video_names.append(info.filename)
            elif extension in AUDIO_EXTENSIONS:
                audio_names.append(info.filename)

        stored_files = store_media_files(
            archive, infos, hashlib.sha1(data).hexdigest(), files_directory()
        )

        if not text_names:
            raise ArchiveError(
                "No chat log (_chat.txt) found in the archive. Is this a WhatsApp "
                "'Export chat' .zip that includes the chat text?"
            )

        chat_log = text_names[_pick_chat_log(text_names)]
        raw = archive.read(chat_log)

        images: dict[str, bytes] = {}
        total = 0
        for name in image_names:
            info = archive.getinfo(name)
            total += info.file_size
            if total > MAX_ARCHIVE_BYTES:
                break
            try:
                payload = archive.read(name)
            except Exception:  # damaged entry: keep going with the rest
                continue
            base = os.path.basename(name.replace("\\", "/"))
            images.setdefault(base.lower(), payload)

        videos: dict[str, bytes] = {}
        video_total = 0
        for name in video_names:
            info = archive.getinfo(name)
            video_total += info.file_size
            if video_total > MAX_VIDEO_TOTAL_BYTES:
                break
            try:
                payload = archive.read(name)
            except Exception:
                continue
            base = os.path.basename(name.replace("\\", "/"))
            videos.setdefault(base.lower(), payload)

        audios: dict[str, bytes] = {}
        audio_total = 0
        for name in audio_names:
            info = archive.getinfo(name)
            audio_total += info.file_size
            if info.file_size > MAX_AUDIO_FILE_BYTES or audio_total > MAX_AUDIO_TOTAL_BYTES:
                continue
            try:
                payload = archive.read(name)
            except Exception:
                continue
            base = os.path.basename(name.replace("\\", "/"))
            audios.setdefault(base.lower(), payload)

    messages = parse_chat(decode_export(raw))
    chat_name = os.path.splitext(os.path.basename(chat_log.replace("\\", "/")))[0]
    return ChatExport(
        messages=messages,
        images=images,
        videos=videos,
        audios=audios,
        chat_name=chat_name,
        files_dir=str(files_directory()),
        stored_files=stored_files,
    )
