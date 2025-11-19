from io import BytesIO
from pathlib import Path
import subprocess

import pytest
from fastapi import UploadFile

from app.video import (
    InvalidVideoError,
    ProcessingError,
    build_filter_expression,
    render_with_emoji,
)


def test_build_filter_expression_escapes_special_characters() -> None:
    expression = build_filter_expression(r"\:%'50")
    text_segment = expression.split("text='", 1)[1].split("':", 1)[0]

    assert r"\:" in text_segment
    assert r"\%" in text_segment
    assert r"\'" in text_segment
    assert text_segment.count("\\") >= 3
    assert text_segment.endswith("50")


@pytest.mark.asyncio
async def test_render_with_emoji_runs_ffmpeg(monkeypatch, settings) -> None:
    upload = UploadFile(filename="video.mp4", file=BytesIO(b"raw video"))
    recorded = {}

    def fake_run(command, **kwargs):
        recorded["command"] = command
        output_path = Path(command[-1])
        output_path.write_bytes(b"processed")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("app.video.subprocess.run", fake_run)

    result_path = await render_with_emoji(upload, settings)

    assert recorded["command"][0] == settings.ffmpeg_binary
    assert recorded["command"][4] == "-vf"
    assert recorded["command"][5].startswith("drawtext=text='")
    assert result_path.exists()
    assert result_path.read_bytes() == b"processed"
    result_path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_render_with_emoji_rejects_non_mp4(settings) -> None:
    upload = UploadFile(filename="document.mov", file=BytesIO(b"content"))
    with pytest.raises(InvalidVideoError):
        await render_with_emoji(upload, settings)
    await upload.close()


@pytest.mark.asyncio
async def test_render_with_emoji_reports_ffmpeg_failure(monkeypatch, settings, tmp_path):
    stored = {}

    async def fake_persist(upload_file: UploadFile):
        data = await upload_file.read()
        path = tmp_path / "input.mp4"
        path.write_bytes(data)
        stored["path"] = path
        await upload_file.close()
        return path

    def fake_run(command, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=1, cmd=command, stderr=b"boom"
        )

    monkeypatch.setattr("app.video.persist_upload", fake_persist)
    monkeypatch.setattr("app.video.subprocess.run", fake_run)
    upload = UploadFile(filename="video.mp4", file=BytesIO(b"broken"))

    with pytest.raises(ProcessingError) as exc:
        await render_with_emoji(upload, settings)

    assert "boom" in str(exc.value)
    assert not stored["path"].exists()
