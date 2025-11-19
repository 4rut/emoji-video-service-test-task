from collections.abc import Callable

import pytest

from app.config import Settings


@pytest.fixture
def settings_factory() -> Callable[..., Settings]:
    def _factory(**overrides) -> Settings:
        data = {
            "app_host": "0.0.0.0",
            "app_port": 8000,
            "emoji_char": "🙂",
            "bot_backend_url": "http://backend:8000/api/add-emoji",
            "telegram_bot_token": None,
            "max_process_seconds": 5,
            "ffmpeg_binary": "ffmpeg",
        }
        data.update(overrides)
        return Settings(**data)

    return _factory


@pytest.fixture
def settings(settings_factory: Callable[..., Settings]) -> Settings:
    return settings_factory()
