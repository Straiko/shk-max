"""Обработка фото: сканирование штрих-кодов + OCR."""

import logging
import aiohttp
from PIL import Image

from maxapi import Dispatcher, F
from maxapi.types import MessageCreated

from config import Config
from services.scanner import scan_barcodes
from services.ocr import scan_text_ocr
from handlers.barcode import send_barcode_image
from utils.file_manager import temp_image
from utils.rate_limiter import RateLimiter, rate_limit
from utils.db import log_activity

logger = logging.getLogger(__name__)


async def download_photo(bot, message) -> bytes | None:
    """Скачать фото из сообщения MAX."""
    attachments = message.body.attachments
    if not attachments:
        return None

    for att in attachments:
        att_type = getattr(att, "type", None)
        if att_type != "image":
            continue

        payload = getattr(att, "payload", None)
        if not payload:
            continue

        url = getattr(payload, "url", None)
        if not url:
            continue

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.read()
        except Exception:
            logger.exception("Ошибка скачивания фото")
            return None

    return None


def _format_reply(codes: list[str], chosen: str) -> str:
    if len(codes) == 1:
        return f"Найдено:\n\n{chosen}"

    all_codes_text = "\n".join(f"  {c}" for c in codes)
    return (
        f"Найдено (штрих-коды + текст):\n\n"
        f"{all_codes_text}\n\n"
        f"Выбран главный код (самый длинный): {chosen}"
    )


def register(dp: Dispatcher, config: Config, limiter: RateLimiter) -> None:
    @dp.message_created(F.message.body.attachments)
    @rate_limit(limiter)
    async def handle_photo(event: MessageCreated):
        message = event.message
        chat_id = event.chat.chat_id
        attachments = message.body.attachments

        has_image = False
        for att in attachments:
            att_type = getattr(att, "type", None)
            if att_type == "image":
                has_image = True
                break

        if not has_image:
            return

        await event.bot.send_action(chat_id=chat_id, action="typing_on")

        photo_bytes = await download_photo(event.bot, message)
        if photo_bytes is None:
            await event.message.answer("Не удалось скачать фото. Попробуй ещё раз.")
            return

        max_bytes = config.max_file_size_mb * 1024 * 1024
        if len(photo_bytes) > max_bytes:
            await event.message.answer(
                f"Файл слишком большой (максимум {config.max_file_size_mb}MB)."
            )
            return

        with temp_image(suffix=".jpg") as photo_path:
            try:
                photo_path.write_bytes(photo_bytes)
                img = Image.open(photo_path)
                decoded_objects = scan_barcodes(img)
                barcode_codes = [obj.text for obj in decoded_objects]

                ocr_codes = scan_text_ocr(str(photo_path), config.ocr_api_key)

                codes = list(dict.fromkeys(barcode_codes + ocr_codes))

                if not codes:
                    await event.message.answer(
                        "Штрих-коды или текст не найдены на фото.\n"
                        "Попробуй сделать фото чётче."
                    )
                    return

                if barcode_codes:
                    chosen = max(barcode_codes, key=len)
                else:
                    chosen = max(codes, key=len)

                reply = _format_reply(codes, chosen)
                await event.message.answer(reply)
                await send_barcode_image(event.bot, chat_id, chosen)

                sender = message.sender
                user_obj = type('User', (), {
                    'id': getattr(sender, 'user_id', None),
                    'username': getattr(sender, 'username', None),
                    'first_name': getattr(sender, 'first_name', None),
                    'last_name': getattr(sender, 'last_name', None),
                })()
                log_activity(user_obj, "photo", f"Найдено: {chosen}")

            except Exception as e:
                await event.message.answer("Ошибка при обработке фото.")
                logger.exception("Ошибка обработки фото")

    logger.info("Обработчик фото зарегистрирован")
