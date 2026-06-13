"""Генерация штрих-кодов."""

import logging

from maxapi import Dispatcher, F
from maxapi.types import MessageCreated, InputMediaBuffer

import barcode as barcode_lib
from barcode.writer import ImageWriter

from config import Config
from utils.file_manager import temp_image
from utils.db import log_activity

logger = logging.getLogger(__name__)


async def send_barcode_image(bot, chat_id: int, text_to_encode: str) -> None:
    """Сгенерировать Code128 штрих-код и отправить в чат."""
    try:
        with temp_image(suffix=".png") as tmp_path:
            code128 = barcode_lib.get_barcode_class("code128")
            my_barcode = code128(text_to_encode, writer=ImageWriter())
            saved_path = my_barcode.save(str(tmp_path.with_suffix("")))

            with open(saved_path, "rb") as f:
                buffer = f.read()

            await bot.send_message(
                chat_id=chat_id,
                text=f"Штрих-код для: {text_to_encode}",
                attachments=[
                    InputMediaBuffer(buffer=buffer, filename="barcode.png")
                ],
            )
    except Exception as e:
        await bot.send_message(chat_id=chat_id, text="Ошибка при генерации штрих-кода.")
        logger.exception("Ошибка генерации для chat %d", chat_id)


def register(dp: Dispatcher, config: Config, limiter) -> None:
    @dp.message_created(F.message.body.text)
    async def generate_and_send_barcode(event: MessageCreated):
        text_to_encode = event.message.body.text.strip()
        if not text_to_encode or text_to_encode.startswith("/"):
            return

        chat_id = event.chat.chat_id
        await event.bot.send_action(chat_id=chat_id, action="typing_on")
        await send_barcode_image(event.bot, chat_id, text_to_encode)

        sender = event.message.sender
        user_obj = type('User', (), {
            'id': getattr(sender, 'user_id', None),
            'username': getattr(sender, 'username', None),
            'first_name': getattr(sender, 'first_name', None),
            'last_name': getattr(sender, 'last_name', None),
        })()
        log_activity(user_obj, "barcode", f"Создан: {text_to_encode}", chat_id=chat_id)

    logger.info("Обработчик генерации штрих-кодов зарегистрирован")
