"""Unit tests for YouTube Transcript Provider adapter.

BDD Specifications:
- Given a video with available captions,
  When fetching transcript,
  Then raw snippets are converted into clean prose paragraphs.

- Given a video with subtitles disabled or unavailable,
  When fetching transcript,
  Then a TranscriptNotFoundError domain exception is raised.

- Given an IP block or rate limit error (IpBlocked / RequestBlocked),
  When fetching transcript,
  Then a RateLimitExceededError domain exception is raised.
"""

from unittest.mock import MagicMock, patch

import pytest
from youtube_transcript_api import (
    FetchedTranscriptSnippet,
    IpBlocked,
    NoTranscriptFound,
    TranscriptsDisabled,
)

from rhandir.core.domain.exceptions import RateLimitExceededError, TranscriptNotFoundError
from rhandir.core.domain.value_objects.video_id import VideoId
from rhandir.infrastructure.external.youtube_transcript import YouTubeTranscriptProvider


@pytest.mark.asyncio
async def test_given_available_transcript_when_fetching_then_returns_clean_paragraphs() -> None:
    # Given
    provider = YouTubeTranscriptProvider(languages=("pt", "pt-BR", "en"))
    video_id = VideoId("dQw4w9WgXcQ")

    snippets = [
        FetchedTranscriptSnippet(text="Olá a todos.", start=0.0, duration=2.0),
        FetchedTranscriptSnippet(text="Bem-vindos a este vídeo.", start=2.0, duration=2.5),
        FetchedTranscriptSnippet(
            text="Hoje falaremos sobre Clean Architecture.",
            start=4.5,
            duration=3.0,
        ),
    ]

    mock_transcript = MagicMock()
    mock_transcript.__iter__.return_value = iter(snippets)

    with patch.object(provider._api, "fetch", return_value=mock_transcript):
        # When
        paragraphs = await provider.get_transcript(video_id)

        # Then
        assert len(paragraphs) > 0
        joined = " ".join(paragraphs)
        assert "Olá a todos." in joined
        assert "Bem-vindos a este vídeo." in joined
        assert "Clean Architecture." in joined


@pytest.mark.asyncio
async def test_given_disabled_subtitles_when_fetching_then_raises_transcript_not_found() -> None:
    # Given
    provider = YouTubeTranscriptProvider()
    video_id = VideoId("dQw4w9WgXcQ")

    with patch.object(
        provider._api,
        "fetch",
        side_effect=TranscriptsDisabled("dQw4w9WgXcQ"),
    ):
        # When / Then
        with pytest.raises(TranscriptNotFoundError):
            await provider.get_transcript(video_id)


@pytest.mark.asyncio
async def test_given_no_transcript_found_when_fetching_then_raises_transcript_not_found() -> None:
    # Given
    provider = YouTubeTranscriptProvider()
    video_id = VideoId("dQw4w9WgXcQ")

    with patch.object(
        provider._api,
        "fetch",
        side_effect=NoTranscriptFound("dQw4w9WgXcQ", ("pt", "en"), MagicMock()),
    ):
        # When / Then
        with pytest.raises(TranscriptNotFoundError):
            await provider.get_transcript(video_id)


@pytest.mark.asyncio
async def test_given_ip_blocked_when_fetching_then_raises_rate_limit_exceeded() -> None:
    # Given
    provider = YouTubeTranscriptProvider()
    video_id = VideoId("dQw4w9WgXcQ")

    with patch.object(
        provider._api,
        "fetch",
        side_effect=IpBlocked("dQw4w9WgXcQ"),
    ):
        # When / Then
        with pytest.raises(RateLimitExceededError):
            await provider.get_transcript(video_id)
