"""Unit tests for Application Use Cases.

BDD Specifications:
- Given a video with subtitles available,
  When IngestYouTubeVideoUseCase executes,
  Then transcript is fetched, note is written with COMPLETED status, and repository is updated.

- Given a video without subtitles (TranscriptNotFoundError),
  When IngestYouTubeVideoUseCase executes,
  Then note is written with NO_TRANSCRIPT status, and repository is updated accordingly.

- Given a rate limit error (RateLimitExceededError),
  When IngestYouTubeVideoUseCase executes,
  Then the CircuitBreaker is tripped, and record is marked FAILED without crashing the process.

- Given a batch of history videos from Takeout,
  When IngestYouTubeHistoryUseCase executes,
  Then videos are deduplicated against repository and processed sequentially.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from rhandir.application.dtos.video_dto import IngestionSummaryDTO
from rhandir.application.services.circuit_breaker import CircuitBreaker
from rhandir.application.use_cases.ingest_history import IngestYouTubeHistoryUseCase
from rhandir.application.use_cases.ingest_video import IngestYouTubeVideoUseCase
from rhandir.core.domain.entities.video import IngestionRecord, Video
from rhandir.core.domain.exceptions import RateLimitExceededError, TranscriptNotFoundError
from rhandir.core.domain.value_objects.status import IngestionStatus
from rhandir.core.domain.value_objects.video_id import VideoId


@pytest.fixture
def sample_video() -> Video:
    now = datetime(2026, 11, 16, 20, 0, 0, tzinfo=UTC)
    return Video(
        video_id=VideoId("dQw4w9WgXcQ"),
        title="Never Gonna Give You Up",
        channel="Rick Astley",
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        watched_at=now,
        discovered_at=now,
    )


@pytest.mark.asyncio
async def test_given_valid_video_when_ingesting_then_completes_successfully(
    sample_video: Video,
) -> None:
    # Given
    transcript_provider = AsyncMock()
    transcript_provider.get_transcript.return_value = ["Paragraph 1", "Paragraph 2"]

    vault_writer = AsyncMock()
    vault_writer.write_note.return_value = "/vault/note.md"

    repository = AsyncMock()
    repository.get_by_video_id.return_value = IngestionRecord.create_pending(sample_video)

    circuit_breaker = CircuitBreaker(min_delay_seconds=0.0, max_delay_seconds=0.0)

    use_case = IngestYouTubeVideoUseCase(
        transcript_provider=transcript_provider,
        vault_writer=vault_writer,
        repository=repository,
        circuit_breaker=circuit_breaker,
    )

    # When
    record = await use_case.execute(sample_video)

    # Then
    assert record.status == IngestionStatus.COMPLETED
    assert record.vault_path == "/vault/note.md"
    vault_writer.write_note.assert_called_once_with(
        video=sample_video,
        transcript_paragraphs=["Paragraph 1", "Paragraph 2"],
        status=IngestionStatus.COMPLETED,
    )
    repository.update_record.assert_called_once()


@pytest.mark.asyncio
async def test_given_video_without_subtitles_when_ingesting_then_marks_no_transcript(
    sample_video: Video,
) -> None:
    # Given
    transcript_provider = AsyncMock()
    transcript_provider.get_transcript.side_effect = TranscriptNotFoundError("No subs")

    vault_writer = AsyncMock()
    vault_writer.write_note.return_value = "/vault/note_no_sub.md"

    repository = AsyncMock()
    repository.get_by_video_id.return_value = IngestionRecord.create_pending(sample_video)

    circuit_breaker = CircuitBreaker(min_delay_seconds=0.0, max_delay_seconds=0.0)

    use_case = IngestYouTubeVideoUseCase(
        transcript_provider=transcript_provider,
        vault_writer=vault_writer,
        repository=repository,
        circuit_breaker=circuit_breaker,
    )

    # When
    record = await use_case.execute(sample_video)

    # Then
    assert record.status == IngestionStatus.NO_TRANSCRIPT
    assert record.vault_path == "/vault/note_no_sub.md"
    vault_writer.write_note.assert_called_once_with(
        video=sample_video,
        transcript_paragraphs=None,
        status=IngestionStatus.NO_TRANSCRIPT,
    )
    repository.update_record.assert_called_once()


@pytest.mark.asyncio
async def test_given_rate_limit_error_when_ingesting_then_trips_circuit_breaker(
    sample_video: Video,
) -> None:
    # Given
    transcript_provider = AsyncMock()
    transcript_provider.get_transcript.side_effect = RateLimitExceededError("HTTP 429")

    vault_writer = AsyncMock()
    repository = AsyncMock()
    repository.get_by_video_id.return_value = IngestionRecord.create_pending(sample_video)

    circuit_breaker = CircuitBreaker(min_delay_seconds=0.0, max_delay_seconds=0.0)

    use_case = IngestYouTubeVideoUseCase(
        transcript_provider=transcript_provider,
        vault_writer=vault_writer,
        repository=repository,
        circuit_breaker=circuit_breaker,
    )

    # When
    record = await use_case.execute(sample_video)

    # Then
    assert record.status == IngestionStatus.FAILED
    assert circuit_breaker.is_tripped()
    vault_writer.write_note.assert_not_called()
    repository.update_record.assert_called_once()


@pytest.mark.asyncio
async def test_given_history_batch_when_ingesting_then_deduplicates_and_summarizes(
    sample_video: Video,
) -> None:
    # Given
    collector = AsyncMock()
    collector.collect_history.return_value = [sample_video]

    repository = AsyncMock()
    # First check: not exists
    repository.exists.return_value = False
    repository.get_pending_videos.return_value = [sample_video]

    video_use_case = AsyncMock()
    completed_record = IngestionRecord.create_pending(sample_video)
    completed_record.mark_completed(vault_path="/vault/note.md")
    video_use_case.execute.return_value = completed_record

    circuit_breaker = CircuitBreaker(min_delay_seconds=0.0, max_delay_seconds=0.0)

    history_use_case = IngestYouTubeHistoryUseCase(
        collector=collector,
        repository=repository,
        video_use_case=video_use_case,
        circuit_breaker=circuit_breaker,
    )

    # When
    summary = await history_use_case.execute()

    # Then
    assert isinstance(summary, IngestionSummaryDTO)
    assert summary.total_discovered == 1
    assert summary.newly_discovered == 1
    assert summary.completed == 1
    repository.save_discovered.assert_called_once_with(sample_video)
    video_use_case.execute.assert_called_once_with(sample_video)
