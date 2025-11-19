from dataclasses import dataclass
from functools import lru_cache
import os


@dataclass(frozen=True)
class Settings:
    app_host: str
    app_port: int
    emoji_char: str
    bot_backend_url: str
    telegram_bot_token: str | None
    max_process_seconds: int
    ffmpeg_binary: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        app_host=os.getenv("APP_HOST", "0.0.0.0"),
        app_port=int(os.getenv("APP_PORT", "8000")),
        emoji_char=os.getenv("EMOJI_CHAR", "😀"),
        bot_backend_url=os.getenv(
            "BOT_BACKEND_URL", "http://backend:8000/api/add-emoji"
        ),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        max_process_seconds=int(os.getenv("MAX_PROCESS_SECONDS", "90")),
        ffmpeg_binary=os.getenv("FFMPEG_BINARY", "ffmpeg"),
    )
