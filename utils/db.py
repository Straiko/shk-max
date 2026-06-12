"""Модуль для работы со статистикой бота (SQLite)."""

import sqlite3
import datetime
import threading
from typing import Any

db_lock = threading.Lock()
DB_PATH = "bot_data.db"


def init_db() -> None:
    """Инициализация базы данных."""
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    last_seen TIMESTAMP,
                    request_count INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS activity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT,
                    details TEXT,
                    file_id TEXT,
                    timestamp TIMESTAMP
                )
            """)
            try:
                conn.execute("ALTER TABLE activity ADD COLUMN details TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE activity ADD COLUMN file_id TEXT")
            except sqlite3.OperationalError:
                pass
            conn.commit()


def log_activity(user: Any, action: str, details: str = "", file_id: str | None = None) -> None:
    """Логирование действия пользователя."""
    tz_msk = datetime.timezone(datetime.timedelta(hours=3))
    now = datetime.datetime.now(tz_msk).isoformat()
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT INTO users (user_id, username, first_name, last_name, last_seen, request_count)
                VALUES (?, ?, ?, ?, ?, 1)
                ON CONFLICT(user_id) DO UPDATE SET
                    username=excluded.username,
                    first_name=excluded.first_name,
                    last_name=excluded.last_name,
                    last_seen=excluded.last_seen,
                    request_count=request_count+1
            """, (user.id, user.username, user.first_name, user.last_name, now))

            conn.execute("""
                INSERT INTO activity (user_id, action, details, file_id, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (user.id, action, details, file_id, now))
            conn.commit()


def get_stats() -> dict[str, int]:
    """Получение общей статистики."""
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            total_users = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]

            tz_msk = datetime.timezone(datetime.timedelta(hours=3))
            today = datetime.datetime.now(tz_msk).strftime("%Y-%m-%d")

            today_users = conn.execute(
                "SELECT COUNT(DISTINCT user_id) as c FROM activity WHERE substr(timestamp, 1, 10) = ?",
                (today,)
            ).fetchone()["c"]
            total_requests = conn.execute("SELECT SUM(request_count) as c FROM users").fetchone()["c"] or 0

            return {
                "total_users": total_users,
                "today_users": today_users,
                "total_requests": total_requests
            }


def get_users(limit: int = 50, offset: int = 0) -> list[dict]:
    """Список пользователей."""
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM users ORDER BY last_seen DESC LIMIT ? OFFSET ?",
                (limit, offset)
            ).fetchall()
            return [dict(row) for row in rows]


def get_user_activity(user_id: int, limit: int = 50) -> list[dict]:
    """Активность конкретного пользователя."""
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM activity WHERE user_id=? ORDER BY timestamp DESC LIMIT ?",
                (user_id, limit)
            ).fetchall()
            return [dict(row) for row in rows]


def get_recent_activity(limit: int = 15) -> list[dict]:
    """Последняя активность всех пользователей."""
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT a.id, a.user_id, a.action, a.details, a.file_id, a.timestamp, u.username, u.first_name
                FROM activity a
                LEFT JOIN users u ON a.user_id = u.user_id
                ORDER BY a.timestamp DESC LIMIT ?
            """, (limit,)).fetchall()
            return [dict(row) for row in rows]


def get_activity_by_id(act_id: int) -> dict | None:
    """Получить действие по ID."""
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM activity WHERE id=?", (act_id,)).fetchone()
            return dict(row) if row else None


def delete_last_activities(limit: int = 5) -> None:
    """Очистить последние N действий."""
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                DELETE FROM activity
                WHERE id IN (
                    SELECT id FROM activity ORDER BY timestamp DESC LIMIT ?
                )
            """, (limit,))
            conn.commit()


def get_all_user_ids() -> list[int]:
    """Получить все ID пользователей для рассылки."""
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute("SELECT user_id FROM users").fetchall()
            return [row[0] for row in rows]
