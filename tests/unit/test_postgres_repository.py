"""Unit tests for PostgresIngestionRepository with asyncpg mocking.

BDD Specifications:
- Given an asyncpg connection pool,
  When init_schema() is called,
  Then the idempotent DDL table and index creation queries are executed.

- Given a Video domain entity,
  When save_discovered() is called,
  Then an INSERT query is executed with ON CONFLICT DO NOTHING and an IngestionRecord is returned.

- Given an IngestionRecord marked as COMPLETED,
  When update_record() is called,
  Then the record's status, vault_path, and completed_at are updated in PostgreSQL.

- Given rows returned from status aggregation,
  When get_status_counts() is called,
  Then a dictionary mapping status to integer count is produced.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from rhandir.core.domain.entities.video import IngestionRecord, Video
from rhandir.core.domain.value_objects.status import IngestionStatus
from rhandir.core.domain.value_objects.video_id import VideoId
from rhandir.infrastructure.db.postgres_repository import PostgresIngestionRepository


@pytest.fixture
def mock_pool() -> MagicMock:
    pool = MagicMock()
    conn = AsyncMock()
    # Support async with pool.acquire() as conn:
    pool.acquire.return_value.__aenter__.return_value = conn
    return pool


@pytest.mark.asyncio
async def test_given_pool_when_initializing_schema_then_executes_ddl(mock_pool: MagicMock) -> None:
    # Given
    repo = PostgresIngestionRepository(mock_pool)
    conn = mock_pool.acquire.return_value.__aenter__.return_value

    # When
    await repo.init_schema()

    # Then
    assert conn.execute.call_count >= 2
    executed_queries = [call[0][0] for call in conn.execute.call_args_list]
    assert any("CREATE TABLE IF NOT EXISTS youtube_ingestion" in q for q in executed_queries)
    assert any(
        "CREATE INDEX IF NOT EXISTS idx_youtube_ingestion_status" in q for q in executed_queries
    )


@pytest.mark.asyncio
async def test_given_video_when_saving_discovered_then_inserts_record(mock_pool: MagicMock) -> None:
    # Given
    repo = PostgresIngestionRepository(mock_pool)
    conn = mock_pool.acquire.return_value.__aenter__.return_value

    now = datetime(2026, 11, 16, 20, 0, 0, tzinfo=UTC)
    video = Video(
        video_id=VideoId("dQw4w9WgXcQ"),
        title="Never Gonna Give You Up",
        channel="Rick Astley",
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        watched_at=now,
        discovered_at=now,
    )

    # When
    record = await repo.save_discovered(video)

    # Then
    assert record.video == video
    assert record.status == IngestionStatus.PENDING
    conn.execute.assert_called_once()
    query = conn.execute.call_args[0][0]
    assert "INSERT INTO youtube_ingestion" in query
    assert "ON CONFLICT (video_id) DO NOTHING" in query


@pytest.mark.asyncio
async def test_given_completed_record_when_updating_then_executes_update(
    mock_pool: MagicMock,
) -> None:
    # Given
    repo = PostgresIngestionRepository(mock_pool)
    conn = mock_pool.acquire.return_value.__aenter__.return_value

    now = datetime(2026, 11, 16, 20, 0, 0, tzinfo=UTC)
    video = Video(
        video_id=VideoId("dQw4w9WgXcQ"),
        title="Never Gonna Give You Up",
        channel="Rick Astley",
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        watched_at=now,
        discovered_at=now,
    )
    record = IngestionRecord.create_pending(video)
    record.mark_completed(vault_path="/path/note.md")

    # When
    await repo.update_record(record)

    # Then
    conn.execute.assert_called_once()
    query = conn.execute.call_args[0][0]
    assert "UPDATE youtube_ingestion" in query
    args = conn.execute.call_args[0][1:]
    assert args[0] == IngestionStatus.COMPLETED.value
    assert args[5] == "/path/note.md"
    assert args[7] == "dQw4w9WgXcQ"


@pytest.mark.asyncio
async def test_given_status_rows_when_fetching_status_counts_then_returns_dict(
    mock_pool: MagicMock,
) -> None:
    # Given
    repo = PostgresIngestionRepository(mock_pool)
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    conn.fetch.return_value = [
        {"status": "completed", "count": 42},
        {"status": "no_transcript", "count": 5},
        {"status": "pending", "count": 2},
    ]

    # When
    counts = await repo.get_status_counts()

    # Then
    assert counts == {"completed": 42, "no_transcript": 5, "pending": 2}
