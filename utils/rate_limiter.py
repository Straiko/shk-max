"""Декоратор rate limiting для защиты от спама."""

import time
import logging
from functools import wraps
from threading import Lock
from typing import Callable

logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self, interval_seconds: int = 2) -> None:
        self._interval = interval_seconds
        self._user_timestamps: dict[int, float] = {}
        self._lock = Lock()

    def is_allowed(self, user_id: int) -> bool:
        current_time = time.time()
        with self._lock:
            if len(self._user_timestamps) > 1000:
                self._user_timestamps = {
                    uid: ts for uid, ts in self._user_timestamps.items()
                    if current_time - ts < self._interval * 10
                }

            last_time = self._user_timestamps.get(user_id, 0)
            if current_time - last_time < self._interval:
                return False
            self._user_timestamps[user_id] = current_time
            return True


def rate_limit(limiter: RateLimiter) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(event, *args, **kwargs):
            user_id = event.message.sender.user_id if hasattr(event, "message") and hasattr(event.message, "sender") else None
            if user_id and not limiter.is_allowed(user_id):
                await event.message.answer("Подожди немного, не спеши!")
                return None
            return await func(event, *args, **kwargs)
        return wrapper
    return decorator
