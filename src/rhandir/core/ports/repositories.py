"""Core Repository Ports."""

from typing import Protocol

from rhandir.core.domain.entities.video import IngestionRecord, Video
from rhandir.core.domain.value_objects.video_id import VideoId


class IIngestionRepository(Protocol):
    """Abstract port for persisting and tracking ingestion status."""

    async def init_schema(self) -> None:
        """Ensure database table and indices are initialized idempotently."""
        ...

    async def get_by_video_id(self, video_id: VideoId) -> IngestionRecord | None:
        """Fetch record by video ID if it exists."""
        ...

    async def exists(self, video_id: VideoId) -> bool:
        """Check if video was already recorded."""
        ...

    async def save_discovered(self, video: Video) -> IngestionRecord:
        """Insert or register newly discovered video with PENDING status."""
        ...

    async def update_record(self, record: IngestionRecord) -> None:
        """Update existing record status, timestamps, and error messages."""
        ...

    async def get_pending_videos(self, limit: int = 50) -> list[Video]:
        """Fetch pending videos awaiting transcription."""
        ...

    async def get_status_counts(self) -> dict[str, int]:
        """Fetch count of records grouped by status for observability."""
        ...
