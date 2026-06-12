"""Команда /admin для просмотра статистики и активности."""

import logging

from maxapi import Dispatcher, F
from maxapi.types import MessageCreated, Command, MessageCallback
from maxapi.types.attachments.buttons.callback_button import CallbackButton
from maxapi.filters.callback_payload import CallbackPayload
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from config import Config
from utils.rate_limiter import RateLimiter, rate_limit
from utils.db import (
    get_stats, get_recent_activity, get_users,
    get_activity_by_id, delete_last_activities
)

logger = logging.getLogger(__name__)


class AdminPayload(CallbackPayload, prefix="admin"):
    """Payload для кнопок админ-панели."""
    action: str


def get_admin_keyboard() -> InlineKeyboardBuilder:
    """Создает клавиатуру (меню) админки."""
    kb = InlineKeyboardBuilder()
    kb.row(
        CallbackButton(text="📊 Статистика", payload=AdminPayload(action="stats").pack()),
        CallbackButton(text="📝 Действия", payload=AdminPayload(action="activity").pack()),
    )
    kb.row(
        CallbackButton(text="👥 Пользователи", payload=AdminPayload(action="users").pack()),
        CallbackButton(text="❌ Закрыть", payload=AdminPayload(action="close").pack()),
    )
    return kb


def register(dp: Dispatcher, config: Config, limiter: RateLimiter) -> None:
    """Регистрация команды /admin и её кнопок."""

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

    @dp.message_callback(AdminPayload.filter())
    async def handle_admin_callbacks(event: MessageCallback, payload: AdminPayload):
        user_id = event.callback.user.user_id if event.callback.user else None
        if not is_admin(user_id):
            await event.answer(notification="⛔ Нет доступа.")
            return

        action = payload.action

        if action == "close":
            await event.edit(text="Админ-панель закрыта.", attachments=[])
            await event.answer()
            return

        elif action == "main":
            await event.edit(
                text="👋 Панель администратора\n\nВыберите нужный раздел:",
                attachments=[get_admin_keyboard().as_markup()],
            )
            await event.answer()
            return

        elif action == "stats":
            stats = get_stats()
            text = (
                "📊 Общая статистика:\n\n"
                f"👥 Всего юзеров: {stats['total_users']}\n"
                f"📅 Уникальных сегодня: {stats['today_users']}\n"
                f"🔄 Всего запросов: {stats['total_requests']}\n"
            )
            await event.edit(
                text=text,
                attachments=[get_admin_keyboard().as_markup()],
            )
            await event.answer()
            return

        elif action == "activity":
            activity = get_recent_activity(50)
            if not activity:
                text = "📝 Последние действия:\n\nПусто."
                await event.edit(
                    text=text,
                    attachments=[get_admin_keyboard().as_markup()],
                )
            else:
                lines = []
                kb = InlineKeyboardBuilder()
                photo_buttons = []

                for a in activity:
                    time_str = a['timestamp'][11:19] if a['timestamp'] else "??:??:??"
                    name = a.get('first_name') or a.get('username') or "Без имени"
                    act_icon = "📷" if "photo" in (a['action'] or "") else "📝"
                    details = a.get('details') or "Нет данных"

                    if a.get('file_id'):
                        lines.append(f"{time_str} | {act_icon} {name[:12]} (Акт #{a['id']})\n  {details}")
                        photo_buttons.append(
                            CallbackButton(text=f"📸 #{a['id']}", payload=AdminPayload(action=f"photo_{a['id']}").pack())
                        )
                    else:
                        lines.append(f"{time_str} | {act_icon} {name[:12]}\n  {details}")

                text = "📝 Последние 50 действий:\n\n" + "\n\n".join(lines)
                if len(text) > 4000:
                    text = text[:4000] + "\n... (обрезано)"

                for i in range(0, len(photo_buttons), 5):
                    kb.row(*photo_buttons[i:i + 5])

                kb.row(CallbackButton(text="🗑 Очистить последние 5", payload=AdminPayload(action="clear_5").pack()))
                kb.row(CallbackButton(text="⬅️ В главное меню", payload=AdminPayload(action="main").pack()))

                await event.edit(text=text, attachments=[kb.as_markup()])

        elif action == "clear_5":
            delete_last_activities(5)
            await event.answer(notification="✅ Последние 5 действий удалены!")
            activity = get_recent_activity(50)
            if not activity:
                text = "📝 Последние действия:\n\nПусто."
                await event.edit(
                    text=text,
                    attachments=[get_admin_keyboard().as_markup()],
                )
            else:
                lines = []
                kb = InlineKeyboardBuilder()
                photo_buttons = []

                for a in activity:
                    time_str = a['timestamp'][11:19] if a['timestamp'] else "??:??:??"
                    name = a.get('first_name') or a.get('username') or "Без имени"
                    act_icon = "📷" if "photo" in (a['action'] or "") else "📝"
                    details = a.get('details') or "Нет данных"

                    if a.get('file_id'):
                        lines.append(f"{time_str} | {act_icon} {name[:12]} (Акт #{a['id']})\n  {details}")
                        photo_buttons.append(
                            CallbackButton(text=f"📸 #{a['id']}", payload=AdminPayload(action=f"photo_{a['id']}").pack())
                        )
                    else:
                        lines.append(f"{time_str} | {act_icon} {name[:12]}\n  {details}")

                text = "📝 Последние 50 действий:\n\n" + "\n\n".join(lines)
                if len(text) > 4000:
                    text = text[:4000] + "\n... (обрезано)"

                for i in range(0, len(photo_buttons), 5):
                    kb.row(*photo_buttons[i:i + 5])

                kb.row(CallbackButton(text="🗑 Очистить последние 5", payload=AdminPayload(action="clear_5").pack()))
                kb.row(CallbackButton(text="⬅️ В главное меню", payload=AdminPayload(action="main").pack()))

                await event.edit(text=text, attachments=[kb.as_markup()])
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
            kb.row(CallbackButton(text="⬅️ Назад в действия", payload=AdminPayload(action="activity").pack()))

            photo_url = row['file_id']
            text = f"📝 Лог #{act_id}: {row.get('details', '')}\n\n🔗 Фото: {photo_url}"

            await event.edit(text=text, attachments=[kb.as_markup()])
            await event.answer()
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

            await event.edit(
                text=text,
                attachments=[get_admin_keyboard().as_markup()],
            )

        await event.answer()

    logger.info("Обработчик админки зарегистрирован")
