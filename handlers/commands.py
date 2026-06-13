"""Обработчики команд /start, /help, /version."""

import logging
from maxapi import Dispatcher, F
from maxapi.types import MessageCreated, BotStarted, Command

from config import Config
from utils.db import log_activity

logger = logging.getLogger(__name__)

CHANGELOG = (
    "v3.1.0 -- Портировано на MAX API\n"
    "v3.0.0 -- Рефакторинг: модульная архитектура, безопасность, логирование\n"
    "v2.0.0 -- Production Ready: многопоточность, rate limiting, автоочистка\n"
    "v1.5.2 -- Автоисправление ошибки OCR\n"
    "v1.5.0 -- Умный фильтр текста\n"
    "v1.2.0 -- Генерация баркода после фото\n"
    "v1.1.0 -- Чтение ШК/QR с фото"
)

HELP_TEXT = (
    "Привет! Я умею находить штрих-коды и текст на фото и генерировать новые!\n\n"
    "📷 Читать штрих-коды\n"
    "Просто отправь мне фото или скан (картинкой или файлом).\n"
    "Я найду на нём штрих-коды или текст и выдам результат.\n\n"
    "✏️ Создать штрих-код\n"
    "Отправь любой текст (латиницу или цифры), и я сделаю из него штрих-код.\n\n"
    "⚡️ Команды:\n"
    "/version — версия бота\n"
    "/myid — твой user_id\n"
    "/help — эта справка\n\n"
    "📱 Также доступен в:\n"
    "Telegram: https://t.me/Ozonbratik_bot\n"
    "VK: https://vk.com/club239550562"
)


def register(dp: Dispatcher, config: Config) -> None:
    @dp.bot_started()
    async def handle_bot_started(event: BotStarted):
        await bot_send(event, HELP_TEXT)
        chat_id = event.chat_id
        user_obj = type('User', (), {
            'id': 0,
            'username': None,
            'first_name': None,
            'last_name': None,
        })()
        log_activity(user_obj, "command", "bot_started", chat_id=chat_id)

    @dp.message_created(Command("version"))
    async def send_version(event: MessageCreated):
        text = (
            f"Версия бота: {config.version}\n\n"
            f"История изменений:\n{CHANGELOG}"
        )
        await event.message.answer(text)

    @dp.message_created(Command("start", "help"))
    async def send_welcome(event: MessageCreated):
        await event.message.answer(HELP_TEXT)
        sender = event.message.sender
        user_obj = type('User', (), {
            'id': getattr(sender, 'user_id', None),
            'username': getattr(sender, 'username', None),
            'first_name': getattr(sender, 'first_name', None),
            'last_name': getattr(sender, 'last_name', None),
        })()
        log_activity(user_obj, "command", "/start или /help", chat_id=event.chat_id)

    @dp.message_created(Command("myid"))
    async def send_myid(event: MessageCreated):
        user_id = event.message.sender.user_id if event.message.sender else "неизвестен"
        await event.message.answer(f"Твой user_id: {user_id}")

    logger.info("Обработчики команд зарегистрированы")


async def bot_send(event, text):
    await event.bot.send_message(chat_id=event.chat_id, text=text)
