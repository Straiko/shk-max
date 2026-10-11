import pytest
from config import load_config


def test_config_fails_without_token(monkeypatch):
    monkeypatch.delenv("MAX_BOT_TOKEN", raising=False)
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    with pytest.raises(SystemExit):
        load_config()


def test_config_loads_with_bot_token(monkeypatch):
    monkeypatch.delenv("MAX_BOT_TOKEN", raising=False)
    monkeypatch.setenv("BOT_TOKEN", "test-token-123")
    config = load_config()
    assert config.bot_token == "test-token-123"


def test_config_loads_with_max_bot_token(monkeypatch):
    monkeypatch.setenv("MAX_BOT_TOKEN", "max-token-456")
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    config = load_config()
    assert config.bot_token == "max-token-456"
