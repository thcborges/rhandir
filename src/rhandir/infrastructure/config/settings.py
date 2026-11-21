"""Typed Application Configuration using Pydantic Settings."""

from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/rhandir",
        description="PostgreSQL connection string with WAL mode recommended.",
    )
    obsidian_raw_dir: Path = Field(
        default=Path("inbox/raw_machine"),
        description="Target destination folder in Obsidian vault for raw markdown notes.",
    )
    rclone_vault_remote: str = Field(
        default="gdrive:Obsidian",
        description="Remote Google Drive path configured via rclone for Obsidian vault sync.",
    )
    takeout_inbox_dir: Path = Field(
        default=Path("inbox/takeout"),
        description="Folder monitored for Google Takeout JSON/HTML history files.",
    )
    cookies_file_path: Path | None = Field(
        default=None,
        description="Optional path to Netscape cookies.txt file for authenticated session.",
    )
    daemon_poll_interval_seconds: int = Field(
        default=60,
        description="Interval in seconds between background daemon cycles.",
    )
    transcript_rate_limit_delay_min: float = Field(
        default=2.0,
        description="Minimum delay with jitter between consecutive transcript requests.",
    )
    transcript_rate_limit_delay_max: float = Field(
        default=5.0,
        description="Maximum delay with jitter between consecutive transcript requests.",
    )
    circuit_breaker_backoff_minutes: int = Field(
        default=15,
        description="Duration to pause ingestion if YouTube IP block or HTTP 429 is encountered.",
    )
    telegram_bot_token: str | None = Field(
        default=None,
        description="Telegram Bot API Token to listen for incoming video messages.",
    )
    telegram_allowed_chat_ids: list[int] = Field(
        default_factory=list,
        description="Authorized Telegram chat IDs. If empty, all chats are allowed.",
    )

    @field_validator("telegram_allowed_chat_ids", mode="before")
    @classmethod
    def parse_allowed_chat_ids(cls, v: Any) -> list[int]:
        """Support single int, JSON list, or comma-separated string for chat IDs."""
        if isinstance(v, int):
            return [v]
        if isinstance(v, str):
            v_clean = v.strip()
            if not v_clean:
                return []
            if v_clean.startswith("[") and v_clean.endswith("]"):
                import json

                try:
                    parsed = json.loads(v_clean)
                    return [int(x) for x in parsed]
                except Exception:
                    pass
            return [int(x.strip()) for x in v_clean.split(",") if x.strip()]
        return v

    log_level: str = Field(
        default="INFO",
        description="Structured logging level (DEBUG, INFO, WARNING, ERROR).",
    )
