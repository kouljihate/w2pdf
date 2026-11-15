"""Media helpers for the export: pull a still frame out of a video attachment.

WhatsApp exports include videos as `VID-YYYYMMDD-WA####.mp4`. A PDF page cannot
hold a video, so one representative frame is extracted with ffmpeg (bundled by
`imageio-ffmpeg`, with a system ffmpeg as fallback).
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

FRAME_TIMESTAMPS = ("0.5", "0")
MAX_FRAME_PX = 1600
TIMEOUT_SECONDS = 60


@lru_cache(maxsize=1)
def ffmpeg_path() -> str | None:
    """Locate an ffmpeg binary: the bundled one first, then PATH."""
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg")


def extract_video_frame(data: bytes, max_px: int = MAX_FRAME_PX) -> bytes | None:
    """Return a JPEG frame from the video bytes, or None when it cannot be read."""
    if not data:
        return None
    executable = ffmpeg_path()
    if not executable:
        return None

    with tempfile.TemporaryDirectory() as workdir:
        source = Path(workdir) / "video.bin"
        source.write_bytes(data)
        target = Path(workdir) / "frame.jpg"
        for timestamp in FRAME_TIMESTAMPS:
            command = [
                executable,
                "-y",
                "-loglevel",
                "error",
                "-ss",
                timestamp,
                "-i",
                str(source),
                "-frames:v",
                "1",
                "-vf",
                f"scale='min({max_px},iw)':-2",
                str(target),
            ]
            try:
                subprocess.run(command, check=True, capture_output=True, timeout=TIMEOUT_SECONDS)
            except Exception:
                continue
            if target.exists() and target.stat().st_size:
                return target.read_bytes()
    return None
