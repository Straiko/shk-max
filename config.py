"""Конфигурация бота — загрузка из .env файла."""

import os
import sys
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Config:
    ocr_api_key: str = "helloworld"
    rate_limit_seconds: int = 2
    max_file_size_mb: int = 20
    admin_user_id: int | None = None
    version: str = "3.1.0"


def load_config() -> Config:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        logger.warning("python-dotenv не установлен")

    token = os.getenv("MAX_BOT_TOKEN")
    if not token:
        logger.critical("MAX_BOT_TOKEN не задан! Создайте .env файл (см. .env.example)")
        sys.exit(1)

    admin_id_str = os.getenv("ADMIN_USER_ID")
    admin_user_id = int(admin_id_str) if admin_id_str else None

    return Config(
        ocr_api_key=os.getenv("OCR_API_KEY", "helloworld"),
        rate_limit_seconds=int(os.getenv("RATE_LIMIT_SECONDS", "2")),
        max_file_size_mb=int(os.getenv("MAX_FILE_SIZE_MB", "20")),
        admin_user_id=admin_user_id,
    )
