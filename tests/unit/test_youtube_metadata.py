"""Unit tests for YouTubeMetadataProvider adapter using YouTube oEmbed.

BDD Specifications:
- Given a valid VideoId and a successful YouTube oEmbed HTTP response,
  When get_metadata is invoked,
  Then it returns (title, channel) extracted from the oEmbed payload.

- Given a YouTube video ID that returns 404 or an HTTP error,
  When get_metadata is invoked,
  Then it returns safe fallback values without raising an unhandled exception.

- Given a network timeout or connection failure,
  When get_metadata is invoked,
  Then it returns safe fallback values gracefully.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from rhandir.core.domain.value_objects.video_id import VideoId
from rhandir.infrastructure.external.youtube_metadata import YouTubeMetadataProvider


@pytest.mark.asyncio
async def test_given_valid_video_when_oembed_succeeds_then_returns_title_and_channel() -> None:
    # Given
    provider = YouTubeMetadataProvider()
    video_id = VideoId("dQw4w9WgXcQ")

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "title": "Rick Astley - Never Gonna Give You Up",
        "author_name": "Rick Astley",
    }
    mock_response.raise_for_status.return_value = None

    with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        # When
        title, channel = await provider.get_metadata(video_id)

    # Then
    assert title == "Rick Astley - Never Gonna Give You Up"
    assert channel == "Rick Astley"


@pytest.mark.asyncio
async def test_given_http_error_when_fetching_metadata_then_returns_fallback() -> None:
    # Given
    provider = YouTubeMetadataProvider()
    video_id = VideoId("12345678901")

    with patch.object(
        httpx.AsyncClient,
        "get",
        side_effect=httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(spec=httpx.Request),
            response=MagicMock(spec=httpx.Response, status_code=404),
        ),
    ):
        # When
        title, channel = await provider.get_metadata(video_id)

    # Then
    assert title == "YouTube Video 12345678901"
    assert channel == "Canal Desconhecido"


@pytest.mark.asyncio
async def test_given_timeout_when_fetching_metadata_then_returns_fallback() -> None:
    # Given
    provider = YouTubeMetadataProvider()
    video_id = VideoId("dQw4w9WgXcQ")

    with patch.object(
        httpx.AsyncClient,
        "get",
        side_effect=httpx.TimeoutException("Request timed out"),
    ):
        # When
        title, channel = await provider.get_metadata(video_id)

    # Then
    assert title == "YouTube Video dQw4w9WgXcQ"
    assert channel == "Canal Desconhecido"
