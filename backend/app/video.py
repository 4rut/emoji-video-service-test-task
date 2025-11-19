from pathlib import Path
import os
import subprocess
import tempfile
from typing import Final

from fastapi import UploadFile

from .config import Settings

SUPPORTED_EXTENSION: Final[str] = ".mp4"
FONT_PATH: Final[str] = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"


class InvalidVideoError(ValueError):
    pass


class ProcessingError(RuntimeError):
    pass


async def persist_upload(upload_file: UploadFile) -> Path:
    suffix = Path(upload_file.filename or "").suffix or SUPPORTED_EXTENSION
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    path = Path(tmp_path)
    try:
        with path.open("wb") as buffer:
            while chunk := await upload_file.read(1024 * 1024):
                buffer.write(chunk)
    finally:
        await upload_file.close()
    return path


def _escape_drawtext_value(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", r"\'")
        .replace("%", r"\%")
    )


def build_filter_expression(emoji_char: str) -> str:
    safe_text = _escape_drawtext_value(emoji_char or "😀")
    return (
        "drawtext=text='{text}':"
        "fontsize=min(w\\,h)/3:"
        "fontcolor=white:borderw=8:bordercolor=black:"
        "x=(w-text_w)/2:y=(h-text_h)/2"
    ).format(text=safe_text)


async def render_with_emoji(
    upload_file: UploadFile, settings: Settings
) -> Path:
    if not upload_file.filename or not upload_file.filename.lower().endswith(
        SUPPORTED_EXTENSION
    ):
        raise InvalidVideoError("Only .mp4 files are supported")

    input_path = await persist_upload(upload_file)
    fd, output_tmp = tempfile.mkstemp(suffix=SUPPORTED_EXTENSION)
    os.close(fd)
    output_path = Path(output_tmp)

    filter_expression = build_filter_expression(settings.emoji_char)

    command = [
        settings.ffmpeg_binary,
        "-y",
        "-i",
        str(input_path),
        "-vf",
        filter_expression,
        "-codec:a",
        "copy",
        str(output_path),
    ]

    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            timeout=settings.max_process_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise ProcessingError("ffmpeg processing timed out") from exc
    except subprocess.CalledProcessError as exc:
        raise ProcessingError(exc.stderr.decode("utf-8", errors="ignore")) from exc
    finally:
        if input_path.exists():
            input_path.unlink(missing_ok=True)

    if not output_path.exists():
        raise ProcessingError("Failed to produce processed video")
    return output_path
