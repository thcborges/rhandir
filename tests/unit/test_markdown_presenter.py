"""Unit tests for MarkdownPresenter.

BDD Specifications:
- Given a Video entity and valid transcript paragraphs,
  When MarkdownPresenter formats the note,
  Then it produces canonical Obsidian frontmatter, headers, metadata callouts, and clean prose.

- Given a Video with no transcript and status NO_TRANSCRIPT,
  When MarkdownPresenter formats the note,
  Then it produces frontmatter with status: no_transcript and an Obsidian warning callout.

- Given a title with special filesystem characters,
  When generating filename,
  Then dangerous characters are cleanly sanitized without collision.
"""

from datetime import UTC, datetime

from rhandir.core.domain.entities.video import Video
from rhandir.core.domain.value_objects.status import IngestionStatus
from rhandir.core.domain.value_objects.video_id import VideoId
from rhandir.interfaces.presenters.markdown_presenter import MarkdownPresenter


def test_given_video_with_transcript_when_presenting_then_formats_valid_note() -> None:
    # Given
    now = datetime(2026, 11, 16, 20, 0, 0, tzinfo=UTC)
    video = Video(
        video_id=VideoId("dQw4w9WgXcQ"),
        title="Never Gonna Give You Up: The Story / Live",
        channel="Rick Astley",
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        watched_at=now,
        discovered_at=now,
    )
    paragraphs = [
        "We're no strangers to love. You know the rules and so do I.",
        "A full commitment's what I'm thinking of.",
    ]

    # When
    presenter = MarkdownPresenter()
    content = presenter.format_note(
        video=video,
        transcript_paragraphs=paragraphs,
        status=IngestionStatus.COMPLETED,
        ingested_at=now,
    )

    # Then
    assert 'title: "Never Gonna Give You Up - The Story - Live"' in content
    assert 'source_url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ"' in content
    assert 'channel: "Rick Astley"' in content
    assert 'status: "raw"' in content
    assert 'type: "youtube_video"' in content
    assert "# Never Gonna Give You Up" in content
    assert "> **Canal:** [[Rick Astley]] | **Link:** [YouTube]" in content
    assert "## Transcrição" in content
    assert "We're no strangers to love." in content


def test_given_video_without_transcript_when_presenting_then_includes_warning_callout() -> None:
    # Given
    now = datetime(2026, 11, 16, 20, 0, 0, tzinfo=UTC)
    video = Video(
        video_id=VideoId("dQw4w9WgXcQ"),
        title="Instrumental Track Only",
        channel="Music Channel",
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        watched_at=now,
        discovered_at=now,
    )

    # When
    presenter = MarkdownPresenter()
    content = presenter.format_note(
        video=video,
        transcript_paragraphs=None,
        status=IngestionStatus.NO_TRANSCRIPT,
        ingested_at=now,
    )

    # Then
    assert 'status: "no_transcript"' in content
    assert "> [!WARNING] Transcrição indisponível" in content


def test_given_video_when_generating_filename_then_returns_sanitized_deterministic_name() -> None:
    # Given
    now = datetime(2026, 11, 16, 20, 0, 0, tzinfo=UTC)
    video = Video(
        video_id=VideoId("dQw4w9WgXcQ"),
        title="Aula 01: Como Usar Python/Linux? <Guia Definitivo>",
        channel="Dev Channel",
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        watched_at=now,
        discovered_at=now,
    )

    # When
    presenter = MarkdownPresenter()
    filename = presenter.format_filename(video)

    # Then
    assert (
        filename
        == "2026-11-16 - Aula 01 - Como Usar Python - Linux - Guia Definitivo - dQw4w9WgXcQ.md"
    )
