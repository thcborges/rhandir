"""Typed Application Configuration using Pydantic Settings."""

from pathlib import Path

from pydantic import Field
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
    log_level: str = Field(
        default="INFO",
        description="Structured logging level (DEBUG, INFO, WARNING, ERROR).",
    )
