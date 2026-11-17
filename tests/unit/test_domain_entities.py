"""Unit tests for Core Domain Entities and Value Objects.

BDD Specifications:
- Given a valid 11-character YouTube video ID string,
  When a VideoId value object is instantiated,
  Then it preserves the string and formats the direct YouTube URL.

- Given an invalid video ID string (empty or containing invalid characters),
  When a VideoId value object is instantiated,
  Then an InvalidVideoIdError must be raised.

- Given video metadata,
  When an IngestionRecord entity is instantiated,
  Then its initial status is PENDING and timestamps are correctly tracked on transitions.
"""

from datetime import UTC, datetime

import pytest

from rhandir.core.domain.entities.video import IngestionRecord, Video
from rhandir.core.domain.exceptions import InvalidVideoIdError
from rhandir.core.domain.value_objects.status import IngestionStatus
from rhandir.core.domain.value_objects.video_id import VideoId


def test_given_valid_string_when_creating_video_id_then_succeeds_and_generates_url() -> None:
    # Given
    raw_id = "dQw4w9WgXcQ"

    # When
    video_id = VideoId(raw_id)

    # Then
    assert str(video_id) == "dQw4w9WgXcQ"
    assert video_id.value == "dQw4w9WgXcQ"
    assert video_id.to_url() == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


@pytest.mark.parametrize(
    "invalid_id", ["", "short", "too_long_for_youtube_id_12345", "inv@lid!char"]
)
def test_given_invalid_string_when_creating_video_id_then_raises_domain_error(
    invalid_id: str,
) -> None:
    # Given / When / Then
    with pytest.raises(InvalidVideoIdError):
        VideoId(invalid_id)


def test_given_video_data_when_creating_ingestion_record_then_manages_lifecycle() -> None:
    # Given
    now = datetime.now(UTC)
    video = Video(
        video_id=VideoId("dQw4w9WgXcQ"),
        title="Never Gonna Give You Up",
        channel="Rick Astley",
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        watched_at=now,
        discovered_at=now,
    )

    # When
    record = IngestionRecord.create_pending(video)

    # Then
    assert record.status == IngestionStatus.PENDING
    assert record.completed_at is None
    assert record.vault_path is None

    # When marking completed
    record.mark_completed(vault_path="/vault/00_Inbox/Raw_Machine/note.md")
    assert record.status == IngestionStatus.COMPLETED
    assert record.completed_at is not None
    assert record.vault_path == "/vault/00_Inbox/Raw_Machine/note.md"

    # When marking no_transcript
    record.mark_no_transcript(vault_path="/vault/00_Inbox/Raw_Machine/note_no_transcript.md")
    assert record.status == IngestionStatus.NO_TRANSCRIPT
    assert record.no_transcript_at is not None

    # When marking failed
    record.mark_failed(error_message="HTTP 429 Too Many Requests")
    assert record.status == IngestionStatus.FAILED
    assert record.failed_at is not None
    assert record.error_message == "HTTP 429 Too Many Requests"
    assert record.retry_count == 1
