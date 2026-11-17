"""Ingestion Status Value Object."""

from enum import StrEnum


class IngestionStatus(StrEnum):
    """Lifecycle status of an ingested video."""

    PENDING = "pending"
    COMPLETED = "completed"
    NO_TRANSCRIPT = "no_transcript"
    FAILED = "failed"
