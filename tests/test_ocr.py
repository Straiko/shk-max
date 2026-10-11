"""Тесты для OCR-сервиса Yandex Cloud OCR."""

from services.ocr import _extract_codes, scan_text_ocr


def test_extract_codes_with_valid_barcode():
    result = _extract_codes("ii1234567890")
    assert "ii1234567890" in result


def test_extract_codes_filters_short_text():
    result = _extract_codes("AB12")
    assert result == []


def test_extract_codes_filters_no_digits():
    result = _extract_codes("ABCDEFGH")
    assert result == []


def test_extract_codes_filters_russian():
    result = _extract_codes("Привет мир Тестовый")
    assert result == []


def test_extract_codes_strips_punctuation():
    result = _extract_codes("(ABC12345)")
    assert "ABC12345" in result


def test_extract_codes_ocr_autocorrect():
    result = _extract_codes("i11234567")
    assert "ii1234567" in result


def test_scan_text_ocr_missing_key(monkeypatch, tmp_path):
    monkeypatch.delenv("YANDEX_API_KEY", raising=False)
    img_file = tmp_path / "test.jpg"
    img_file.write_bytes(b"dummy")

    assert scan_text_ocr(str(img_file), api_key=None) == []


def test_scan_text_ocr_invalid_key(monkeypatch, tmp_path):
    monkeypatch.setenv("YANDEX_API_KEY", "K88309127788957")
    img_file = tmp_path / "test.jpg"
    img_file.write_bytes(b"dummy")

    assert scan_text_ocr(str(img_file)) == []


def test_scan_text_ocr_success(monkeypatch, tmp_path):
    monkeypatch.setenv("YANDEX_API_KEY", "AQVN_test_key")
    monkeypatch.setenv("YANDEX_FOLDER_ID", "test-folder")
    img_file = tmp_path / "test.jpg"
    img_file.write_bytes(b"dummy")

    class MockResponse:
        status_code = 200

        def json(self):
            return {
                "result": {
                    "textAnnotation": {
                        "fullText": "Код товара: ii1234567890"
                    }
                }
            }

    monkeypatch.setattr("requests.post", lambda *args, **kwargs: MockResponse())
    result = scan_text_ocr(str(img_file))
    assert result == ["ii1234567890"]
