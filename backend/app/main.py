import logging

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from .config import get_settings
from .video import InvalidVideoError, ProcessingError, render_with_emoji

logger = logging.getLogger(__name__)

app = FastAPI(title="Emoji Video Service")


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/add-emoji", tags=["video"])
async def add_emoji_endpoint(file: UploadFile = File(...)) -> FileResponse:
    settings = get_settings()
    try:
        output_path = await render_with_emoji(file, settings)
    except InvalidVideoError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ProcessingError as exc:
        logger.exception("Video processing failed")
        raise HTTPException(status_code=500, detail="Failed to process video") from exc

    filename = file.filename or "video.mp4"
    task = BackgroundTask(output_path.unlink, missing_ok=True)

    return FileResponse(
        path=output_path,
        media_type="video/mp4",
        filename=f"emoji-{filename}",
        background=task,
    )
