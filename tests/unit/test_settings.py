"""Unit tests for Settings configuration."""

from rhandir.infrastructure.config.settings import Settings


def test_given_default_settings_when_initialized_then_telegram_is_disabled() -> None:
    settings = Settings()
    assert settings.telegram_bot_token is None
    assert settings.telegram_allowed_chat_ids == []


def test_given_custom_telegram_env_when_initialized_then_populates_fields(
    monkeypatch,
) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
    monkeypatch.setenv("TELEGRAM_ALLOWED_CHAT_IDS", "[111222, 333444]")

    settings = Settings()
    assert settings.telegram_bot_token == "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    assert settings.telegram_allowed_chat_ids == [111222, 333444]
