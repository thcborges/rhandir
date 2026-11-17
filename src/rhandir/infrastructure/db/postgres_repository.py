"""PostgreSQL Implementation of IIngestionRepository using asyncpg."""

from typing import Any

import asyncpg

from rhandir.core.domain.entities.video import IngestionRecord, Video
from rhandir.core.domain.value_objects.status import IngestionStatus
from rhandir.core.domain.value_objects.video_id import VideoId
from rhandir.core.ports.repositories import IIngestionRepository

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS youtube_ingestion (
    video_id VARCHAR(32) PRIMARY KEY,
    title TEXT NOT NULL,
    channel TEXT NOT NULL,
    url TEXT NOT NULL,
    status VARCHAR(20) NOT NULL,
    discovered_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    no_transcript_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    error_message TEXT,
    vault_path TEXT,
    retry_count INTEGER DEFAULT 0
);
"""

_CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_youtube_ingestion_status ON youtube_ingestion(status);
"""


class PostgresIngestionRepository(IIngestionRepository):
    """Repository handling deduplication and lifecycle state in PostgreSQL."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def init_schema(self) -> None:
        """Initialize database table and index idempotently."""
        async with self._pool.acquire() as conn:
            await conn.execute(_CREATE_TABLE_SQL)
            await conn.execute(_CREATE_INDEX_SQL)

    def _row_to_record(self, row: dict[str, Any] | asyncpg.Record) -> IngestionRecord:
        """Map database row to domain IngestionRecord."""
        video = Video(
            video_id=VideoId(row["video_id"]),
            title=row["title"],
            channel=row["channel"],
            url=row["url"],
            watched_at=None,
            discovered_at=row["discovered_at"],
        )
        return IngestionRecord(
            video=video,
            status=IngestionStatus(row["status"]),
            completed_at=row["completed_at"],
            no_transcript_at=row["no_transcript_at"],
            failed_at=row["failed_at"],
            error_message=row["error_message"],
            vault_path=row["vault_path"],
            retry_count=row["retry_count"],
        )

    async def get_by_video_id(self, video_id: VideoId) -> IngestionRecord | None:
        """Fetch record by video ID."""
        query = "SELECT * FROM youtube_ingestion WHERE video_id = $1"
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, video_id.value)
            return self._row_to_record(row) if row else None

    async def exists(self, video_id: VideoId) -> bool:
        """Check if video was already recorded."""
        query = "SELECT 1 FROM youtube_ingestion WHERE video_id = $1"
        async with self._pool.acquire() as conn:
            val = await conn.fetchval(query, video_id.value)
            return val is not None

    async def save_discovered(self, video: Video) -> IngestionRecord:
        """Insert newly discovered video with status PENDING, ignoring conflict if exists."""
        query = """
        INSERT INTO youtube_ingestion (
            video_id, title, channel, url, status, discovered_at, retry_count
        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (video_id) DO NOTHING;
        """
        async with self._pool.acquire() as conn:
            await conn.execute(
                query,
                video.video_id.value,
                video.title,
                video.channel,
                video.url,
                IngestionStatus.PENDING.value,
                video.discovered_at,
                0,
            )
        return IngestionRecord.create_pending(video)

    async def update_record(self, record: IngestionRecord) -> None:
        """Update existing record status, timestamps, and error messages."""
        query = """
        UPDATE youtube_ingestion SET
            status = $1,
            completed_at = $2,
            no_transcript_at = $3,
            failed_at = $4,
            error_message = $5,
            vault_path = $6,
            retry_count = $7
        WHERE video_id = $8;
        """
        async with self._pool.acquire() as conn:
            await conn.execute(
                query,
                record.status.value,
                record.completed_at,
                record.no_transcript_at,
                record.failed_at,
                record.error_message,
                record.vault_path,
                record.retry_count,
                record.video.video_id.value,
            )

    async def get_pending_videos(self, limit: int = 50) -> list[Video]:
        """Fetch pending videos awaiting transcription."""
        query = """
        SELECT video_id, title, channel, url, discovered_at
        FROM youtube_ingestion
        WHERE status = 'pending'
        ORDER BY discovered_at ASC
        LIMIT $1;
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, limit)
            return [
                Video(
                    video_id=VideoId(row["video_id"]),
                    title=row["title"],
                    channel=row["channel"],
                    url=row["url"],
                    watched_at=None,
                    discovered_at=row["discovered_at"],
                )
                for row in rows
            ]

    async def get_status_counts(self) -> dict[str, int]:
        """Fetch count of records grouped by status for observability."""
        query = """
        SELECT status, COUNT(*) as count
        FROM youtube_ingestion
        GROUP BY status;
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query)
            return {row["status"]: int(row["count"]) for row in rows}
