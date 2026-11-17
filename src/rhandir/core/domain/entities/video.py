"""Video and IngestionRecord Domain Entities."""

from dataclasses import dataclass
from datetime import UTC, datetime

from rhandir.core.domain.value_objects.status import IngestionStatus
from rhandir.core.domain.value_objects.video_id import VideoId


@dataclass(frozen=True)
class Video:
    """Core domain entity representing a YouTube video discovery."""

    video_id: VideoId
    title: str
    channel: str
    url: str
    watched_at: datetime | None
    discovered_at: datetime


@dataclass
class IngestionRecord:
    """Entity tracking the ingestion lifecycle and state transitions of a video."""

    video: Video
    status: IngestionStatus
    completed_at: datetime | None = None
    no_transcript_at: datetime | None = None
    failed_at: datetime | None = None
    error_message: str | None = None
    vault_path: str | None = None
    retry_count: int = 0

    @classmethod
    def create_pending(cls, video: Video) -> "IngestionRecord":
        """Factory method to instantiate a new pending ingestion record."""
        return cls(video=video, status=IngestionStatus.PENDING)

    def mark_completed(self, vault_path: str) -> None:
        """Transition status to COMPLETED and record destination path."""
        self.status = IngestionStatus.COMPLETED
        self.completed_at = datetime.now(UTC)
        self.vault_path = vault_path
        self.error_message = None

    def mark_no_transcript(self, vault_path: str) -> None:
        """Transition status to NO_TRANSCRIPT when no subtitles exist."""
        self.status = IngestionStatus.NO_TRANSCRIPT
        self.no_transcript_at = datetime.now(UTC)
        self.vault_path = vault_path

    def mark_failed(self, error_message: str) -> None:
        """Transition status to FAILED, record error message and bump retry count."""
        self.status = IngestionStatus.FAILED
        self.failed_at = datetime.now(UTC)
        self.error_message = error_message
        self.retry_count += 1
