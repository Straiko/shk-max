"""Сканирование штрих-кодов и QR-кодов с изображений."""

import logging
from PIL import Image, ImageEnhance
import zxingcpp

logger = logging.getLogger(__name__)


def scan_barcodes(img: Image.Image) -> list:
    try:
        if img.mode != "RGB":
            img = img.convert("RGB")
        gray = img.convert("L")
        w, h = img.size

        attempts = [
            img,
            ImageEnhance.Contrast(gray).enhance(2.0).convert("RGB"),
            ImageEnhance.Sharpness(gray).enhance(3.0).convert("RGB"),
            img.resize((w * 2, h * 2), Image.LANCZOS),
        ]

        for attempt_img in attempts:
            results = zxingcpp.read_barcodes(attempt_img)
            if results:
                return results
    except Exception:
        logger.exception("Ошибка сканирования штрих-кода")

    return []
