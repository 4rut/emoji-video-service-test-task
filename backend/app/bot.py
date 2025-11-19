import asyncio
import logging
from pathlib import Path
import tempfile

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import BufferedInputFile, Message
import httpx

from .config import get_settings

logger = logging.getLogger(__name__)


async def _download_message_video(bot: Bot, message: Message) -> tuple[Path, str]:
    video = message.video or message.document
    if video is None:
        raise ValueError("Нет видео для обработки")

    filename = "video.mp4"
    if message.document:
        filename = message.document.file_name or filename
        if not filename.lower().endswith(".mp4"):
            raise ValueError("Пришлите файл с расширением .mp4")
        if message.document.mime_type not in (None, "video/mp4"):
            raise ValueError("Поддерживается только video/mp4")
    elif message.video:
        filename = f"{message.video.file_unique_id}.mp4"

    fd, tmp_name = tempfile.mkstemp(suffix=".mp4")
    path = Path(tmp_name)
    with path.open("wb") as destination:
        file = await bot.get_file(video.file_id)
        await bot.download(file, destination=destination)
    return path, filename


async def _call_backend(file_path: Path, filename: str) -> bytes:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=settings.max_process_seconds + 30) as client:
        with file_path.open("rb") as payload:
            files = {"file": (filename, payload, "video/mp4")}
            response = await client.post(settings.bot_backend_url, files=files)
            response.raise_for_status()
            return response.content


async def _handle_video(message: Message, bot: Bot) -> None:
    settings = get_settings()
    if not settings.telegram_bot_token:
        await message.answer("Бот не сконфигурирован. Обратитесь к администратору.")
        return

    await message.answer("Видео получено, добавляю смайлик…")
    try:
        temp_path, filename = await _download_message_video(bot, message)
    except ValueError as exc:
        await message.answer(str(exc))
        return
    except Exception:
        logger.exception("Failed to download telegram file")
        await message.answer("Не удалось скачать файл, попробуйте ещё раз.")
        return
    try:
        processed_bytes = await _call_backend(temp_path, filename)
    except httpx.HTTPStatusError as exc:
        logger.exception("Backend error: %s", exc.response.text)
        await message.answer("Не удалось обработать видео. Попробуйте позже.")
        return
    except httpx.HTTPError:
        logger.exception("HTTP error while calling backend")
        await message.answer("Бэкенд недоступен, повторите попытку позднее.")
        return
    finally:
        temp_path.unlink(missing_ok=True)

    await message.answer_video(
        BufferedInputFile(processed_bytes, filename="emoji-" + filename)
    )


async def _cmd_start(message: Message) -> None:
    await message.answer(
        (
            "Отправьте mp4 видео, и я добавлю смайлик по центру. "
        ),
        parse_mode=ParseMode.HTML,
    )


async def run_bot() -> None:
    settings = get_settings()
    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN is not configured. Bot will not start.")
        return

    bot = Bot(token=settings.telegram_bot_token)
    dispatcher = Dispatcher()

    dispatcher.message.register(_cmd_start, CommandStart())
    dispatcher.message.register(_handle_video, F.video | F.document)

    logger.info("Starting Telegram bot polling")
    await dispatcher.start_polling(bot)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
