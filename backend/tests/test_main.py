from io import BytesIO
from pathlib import Path

import pytest
from fastapi import UploadFile
from fastapi import HTTPException
from fastapi.responses import FileResponse

from app import main
from app.video import InvalidVideoError, ProcessingError


@pytest.mark.asyncio
async def test_add_emoji_endpoint_returns_file_response(
    monkeypatch, settings, tmp_path
) -> None:
    output = tmp_path / "result.mp4"
    output.write_bytes(b"framed")

    async def fake_render(upload_file: UploadFile, provided_settings):
        assert provided_settings == settings
        content = await upload_file.read()
        assert content == b"payload"
        return output

    monkeypatch.setattr(main, "get_settings", lambda: settings)
    monkeypatch.setattr(main, "render_with_emoji", fake_render)
    upload = UploadFile(filename="clip.mp4", file=BytesIO(b"payload"))

    response = await main.add_emoji_endpoint(upload)

    assert isinstance(response, FileResponse)
    assert Path(response.path) == output
    assert response.filename == "emoji-clip.mp4"
    assert response.media_type == "video/mp4"


@pytest.mark.asyncio
async def test_add_emoji_endpoint_maps_invalid_video_error(monkeypatch, settings):
    async def fake_render(*_args, **_kwargs):
        raise InvalidVideoError("Only .mp4 files are supported")

    monkeypatch.setattr(main, "get_settings", lambda: settings)
    monkeypatch.setattr(main, "render_with_emoji", fake_render)
    upload = UploadFile(filename="clip.mp4", file=BytesIO(b"payload"))

    with pytest.raises(HTTPException) as exc:
        await main.add_emoji_endpoint(upload)

    assert exc.value.status_code == 400
    assert "Only .mp4 files are supported" == exc.value.detail


@pytest.mark.asyncio
async def test_add_emoji_endpoint_maps_processing_error(monkeypatch, settings):
    async def fake_render(*_args, **_kwargs):
        raise ProcessingError("boom")

    monkeypatch.setattr(main, "get_settings", lambda: settings)
    monkeypatch.setattr(main, "render_with_emoji", fake_render)
    upload = UploadFile(filename="clip.mp4", file=BytesIO(b"payload"))

    with pytest.raises(HTTPException) as exc:
        await main.add_emoji_endpoint(upload)

    assert exc.value.status_code == 500
    assert exc.value.detail == "Failed to process video"
