"""Integration tests for VaultWriter filesystem adapter.

BDD Specifications:
- Given an Obsidian raw directory and video with transcript paragraphs,
  When VaultWriter writes the note asynchronously,
  Then an atomic .md file is saved to disk and its full path is returned.

- Given an invalid output path or filesystem error,
  When VaultWriter writes the note,
  Then a VaultWriteError domain exception is raised.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from rhandir.core.domain.entities.video import Video
from rhandir.core.domain.exceptions import VaultWriteError
from rhandir.core.domain.value_objects.status import IngestionStatus
from rhandir.core.domain.value_objects.video_id import VideoId
from rhandir.infrastructure.filesystem.vault_writer import VaultWriter


@pytest.mark.asyncio
async def test_given_valid_video_when_writing_note_then_creates_atomic_markdown_file(
    tmp_path: Path,
) -> None:
    # Given
    writer = VaultWriter(output_dir=tmp_path)
    now = datetime(2026, 11, 16, 20, 0, 0, tzinfo=UTC)
    video = Video(
        video_id=VideoId("dQw4w9WgXcQ"),
        title="Never Gonna Give You Up",
        channel="Rick Astley",
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        watched_at=now,
        discovered_at=now,
    )
    paragraphs = ["First line of transcript.", "Second line of transcript."]

    # When
    file_path = await writer.write_note(
        video=video,
        transcript_paragraphs=paragraphs,
        status=IngestionStatus.COMPLETED,
    )

    # Then
    path = Path(file_path)
    assert path.exists()
    assert path.parent == tmp_path
    content = path.read_text(encoding="utf-8")
    assert 'title: "Never Gonna Give You Up"' in content
    assert 'source_url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ"' in content
    assert 'channel: "Rick Astley"' in content
    assert "# Never Gonna Give You Up" in content
    expected_callout = (
        "> **Canal:** [[Rick Astley]] | "
        "**Link:** [YouTube](https://www.youtube.com/watch?v=dQw4w9WgXcQ)"
    )
    assert expected_callout in content
    assert "First line of transcript." in content


@pytest.mark.asyncio
async def test_given_read_only_or_invalid_dir_when_writing_note_then_raises_vault_write_error(
    tmp_path: Path,
) -> None:
    # Given: Point writer to a file instead of a directory to force failure
    invalid_file = tmp_path / "not_a_dir"
    invalid_file.write_text("blocking file")
    writer = VaultWriter(output_dir=invalid_file / "subfolder")

    video = Video(
        video_id=VideoId("dQw4w9WgXcQ"),
        title="Test Video",
        channel="Channel",
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        watched_at=datetime.now(UTC),
        discovered_at=datetime.now(UTC),
    )

    # When / Then
    with pytest.raises(VaultWriteError):
        await writer.write_note(
            video=video,
            transcript_paragraphs=None,
            status=IngestionStatus.NO_TRANSCRIPT,
        )
