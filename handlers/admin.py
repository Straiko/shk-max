"""Команда /admin для просмотра статистики и активности."""

import logging

from maxapi import Dispatcher, F
from maxapi.types import MessageCreated, Command, MessageCallback
from maxapi.types.attachments.buttons.callback_button import CallbackButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from config import Config
from utils.rate_limiter import RateLimiter, rate_limit
from utils.db import (
    get_stats, get_recent_activity, get_users,
    get_activity_by_id, delete_last_activities, get_all_user_ids
)

logger = logging.getLogger(__name__)

broadcast_pending = False


def get_admin_keyboard() -> InlineKeyboardBuilder:
    """Создает клавиатуру (меню) админки."""
    kb = InlineKeyboardBuilder()
    kb.row(
        CallbackButton(text="📊 Статистика", payload="admin_stats"),
        CallbackButton(text="📝 Действия", payload="admin_activity"),
    )
    kb.row(
        CallbackButton(text="👥 Пользователи", payload="admin_users"),
        CallbackButton(text="📢 Рассылка", payload="admin_broadcast"),
    )
    kb.row(
        CallbackButton(text="❌ Закрыть", payload="admin_close"),
    )
    return kb


def _format_activity_list(activity: list[dict]) -> tuple[str, InlineKeyboardBuilder]:
    """Форматирует список активности. Возвращает (text, keyboard)."""
    kb = InlineKeyboardBuilder()
    if not activity:
        return "📝 Последние действия:\n\nПусто.", kb

    lines = []
    photo_buttons = []

    for a in activity:
        time_str = a['timestamp'][11:19] if a['timestamp'] else "??:??:??"
        name = a.get('first_name') or a.get('username') or "Без имени"
        act_icon = "📷" if "photo" in (a['action'] or "") else "📝"
        details = a.get('details') or "Нет данных"

        if a.get('file_id'):
            lines.append(f"{time_str} | {act_icon} {name[:12]} (Акт #{a['id']})\n  {details}")
            photo_buttons.append(
                CallbackButton(text=f"📸 #{a['id']}", payload=f"admin_photo_{a['id']}")
            )
        else:
            lines.append(f"{time_str} | {act_icon} {name[:12]}\n  {details}")

    text = "📝 Последние 50 действий:\n\n" + "\n\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n... (обрезано)"

    for i in range(0, len(photo_buttons), 5):
        kb.row(*photo_buttons[i:i + 5])

    kb.row(CallbackButton(text="🗑 Очистить последние 5", payload="admin_clear_5"))
    kb.row(CallbackButton(text="⬅️ В главное меню", payload="admin_main"))
    return text, kb


def register(dp: Dispatcher, config: Config, limiter: RateLimiter) -> None:
    """Регистрация команды /admin и её кнопок."""
    global broadcast_pending

    def is_admin(user_id) -> bool:
        if not config.admin_user_id or user_id is None:
            return False
        return int(user_id) == config.admin_user_id

    @dp.message_created(Command("admin"))
    @rate_limit(limiter)
    async def send_admin_menu(event: MessageCreated):
        user_id = event.message.sender.user_id if event.message.sender else None
        if not is_admin(user_id):
            await event.message.answer("⛔ У вас нет доступа.")
            return

        await event.message.answer(
            "👋 Панель администратора\n\nВыберите нужный раздел:",
            attachments=[get_admin_keyboard().as_markup()],
        )

    @dp.message_created(F.message.body.text)
    async def handle_broadcast_text(event: MessageCreated):
        global broadcast_pending
        if not broadcast_pending:
            return
        broadcast_pending = False
        sender = event.message.sender
        user_id = sender.user_id if sender else None
        if not is_admin(user_id):
            return

        text = event.message.body.text
        if not text:
            return

        user_ids = get_all_user_ids()
        sent = 0
        for uid in user_ids:
            try:
                await event.bot.send_message(
                    chat_id=None,
                    user_id=uid,
                    text=text,
                )
                sent += 1
            except Exception:
                pass

        chat_id = event.message.recipient.chat_id if event.message else None
        await event.bot.send_message(
            chat_id=chat_id,
            user_id=user_id,
            text=f"✅ Рассылка завершена! Отправлено: {sent} из {len(user_ids)}",
            attachments=[get_admin_keyboard().as_markup()],
        )

    @dp.message_callback()
    async def handle_admin_callbacks(event: MessageCallback):
        payload = event.callback.payload if event.callback else None
        if not payload or not payload.startswith("admin_"):
            await event.answer()
            return

        user_id = event.callback.user.user_id if event.callback.user else None
        if not is_admin(user_id):
            await event.answer(notification="⛔ Нет доступа.")
            return

        action = payload.replace("admin_", "", 1)
        chat_id = event.message.recipient.chat_id if event.message else None

        if action == "close":
            await event.answer(notification="✅ Закрыто")
            return

        elif action == "main":
            await event.answer()
            await event.bot.send_message(
                chat_id=chat_id,
                user_id=user_id,
                text="👋 Панель администратора\n\nВыберите нужный раздел:",
                attachments=[get_admin_keyboard().as_markup()],
            )
            return

        elif action == "stats":
            stats = get_stats()
            text = (
                "📊 Общая статистика:\n\n"
                f"👥 Всего юзеров: {stats['total_users']}\n"
                f"📅 Уникальных сегодня: {stats['today_users']}\n"
                f"🔄 Всего запросов: {stats['total_requests']}\n"
            )
            await event.answer()
            await event.bot.send_message(
                chat_id=chat_id,
                user_id=user_id,
                text=text,
                attachments=[get_admin_keyboard().as_markup()],
            )
            return

        elif action == "activity":
            activity = get_recent_activity(50)
            text, kb = _format_activity_list(activity)
            await event.answer()
            await event.bot.send_message(
                chat_id=chat_id,
                user_id=user_id,
                text=text,
                attachments=[kb.as_markup()],
            )
            return

        elif action == "clear_5":
            delete_last_activities(5)
            await event.answer(notification="✅ Удалено!")
            activity = get_recent_activity(50)
            text, kb = _format_activity_list(activity)
            await event.bot.send_message(
                chat_id=chat_id,
                user_id=user_id,
                text=text,
                attachments=[kb.as_markup()],
            )
            return

        elif action.startswith("photo_"):
            try:
                act_id = int(action.split("_")[1])
            except (IndexError, ValueError):
                await event.answer(notification="⚠️ Неверный ID.")
                return

            row = get_activity_by_id(act_id)
            if not row or not row.get('file_id'):
                await event.answer(notification="⚠️ Фото не найдено.")
                return

            kb = InlineKeyboardBuilder()
            kb.row(CallbackButton(text="⬅️ Назад в действия", payload="admin_activity"))

            photo_url = row['file_id']
            text = f"📝 Лог #{act_id}: {row.get('details', '')}\n\n🔗 Фото: {photo_url}"

            await event.answer()
            await event.bot.send_message(
                chat_id=chat_id,
                user_id=user_id,
                text=text,
                attachments=[kb.as_markup()],
            )
            return

        elif action == "users":
            users = get_users(limit=100)
            if not users:
                text = "👥 Последние пользователи:\n\nПусто."
            else:
                lines = []
                for u in users:
                    name = u.get('first_name') or u.get('username') or "Без имени"
                    last_seen = u['last_seen'][11:19] if u.get('last_seen') else "??:??:??"
                    lines.append(f"👤 {name[:15]} | {u['user_id']} | 🕒 {last_seen}")

                text = "👥 Последние 100 заходивших:\n\n" + "\n".join(lines)
                if len(text) > 4000:
                    text = text[:4000] + "\n... (обрезано)"

            await event.answer()
            await event.bot.send_message(
                chat_id=chat_id,
                user_id=user_id,
                text=text,
                attachments=[get_admin_keyboard().as_markup()],
            )
            return

        elif action == "broadcast":
            global broadcast_pending
            broadcast_pending = True
            await event.answer()
            await event.bot.send_message(
                chat_id=chat_id,
                user_id=user_id,
                text="📢 Отправьте текст рассылки\n\nСледующее сообщение будет разослано всем пользователям:",
            )
            return

        await event.answer()

    logger.info("Обработчик админки зарегистрирован")
