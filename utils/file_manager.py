"""Утилиты для работы с временными файлами."""

import tempfile
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

logger = logging.getLogger(__name__)


@contextmanager
def temp_image(suffix: str = ".jpg") -> Generator[Path, None, None]:
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp_path = Path(tmp.name)
    tmp.close()
    try:
        yield tmp_path
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            logger.warning("Не удалось удалить временный файл: %s", tmp_path)
