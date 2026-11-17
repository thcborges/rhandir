"""Data Transfer Objects for Application Layer."""

from dataclasses import dataclass


@dataclass(frozen=True)
class IngestionSummaryDTO:
    """Summary of batch ingestion execution."""

    total_discovered: int
    newly_discovered: int
    completed: int
    no_transcript: int
    failed: int
    skipped_duplicates: int
