"""OCR распознавание текста через OCR.space API."""

import re
import logging
import requests

logger = logging.getLogger(__name__)

OCR_API_URL = "https://api.ocr.space/parse/image"


def scan_text_ocr(photo_path: str, api_key: str) -> list[str]:
    try:
        with open(photo_path, "rb") as f:
            response = requests.post(
                OCR_API_URL,
                files={"file": f},
                data={"apikey": api_key, "language": "eng", "OCREngine": "2"},
                timeout=20,
            )

        if response.status_code != 200:
            logger.warning("OCR API вернул статус %d", response.status_code)
            return []

        result = response.json()
        if not result.get("ParsedResults"):
            return []

        text = result["ParsedResults"][0].get("ParsedText", "")
        return _extract_codes(text)

    except requests.Timeout:
        logger.warning("OCR API timeout")
    except Exception:
        logger.exception("OCR API ошибка")

    return []


def _extract_codes(text: str) -> list[str]:
    codes: list[str] = []

    for word in text.split():
        clean = word.strip(".,;:!?'\"()[]{}")
        clean = re.sub(r"^[iIl1]{2}(?=\d{5,}$)", "ii", clean, flags=re.IGNORECASE)

        if len(clean) > 4 and re.match(r"^[A-Za-z0-9_-]+$", clean):
            if any(c.isdigit() for c in clean):
                codes.append(clean)

    return codes
