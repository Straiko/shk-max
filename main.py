"""
SHK Bot — MAX-бот для сканирования и генерации штрих-кодов.

Точка входа приложения.
"""

import asyncio
import logging

from dotenv import load_dotenv
from maxapi import Bot, Dispatcher

from handlers import commands, photo, barcode
from utils.rate_limiter import RateLimiter
from config import load_config


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("bot.log", encoding="utf-8"),
        ],
    )


async def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)

    load_dotenv()

    config = load_config()
    logger.info("Бот v%s запускается...", config.version)

    bot = Bot()
    dp = Dispatcher()
    limiter = RateLimiter(config.rate_limit_seconds)

    commands.register(dp, config)
    photo.register(dp, config, limiter)
    barcode.register(dp, config, limiter)

    logger.info(
        "Rate limit: %dс | Макс. файл: %dMB",
        config.rate_limit_seconds,
        config.max_file_size_mb,
    )

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
