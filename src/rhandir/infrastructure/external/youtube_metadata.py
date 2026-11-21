"""YouTube Metadata Provider using official oEmbed API via httpx."""

import logging
from typing import Final

import httpx

from rhandir.core.domain.value_objects.video_id import VideoId
from rhandir.core.ports.metadata import IVideoMetadataProvider

logger = logging.getLogger(__name__)

_OEMBED_URL: Final[str] = "https://www.youtube.com/oembed"
_DEFAULT_TIMEOUT: Final[float] = 5.0


class YouTubeMetadataProvider(IVideoMetadataProvider):
    """Fetches video metadata (title, channel) from YouTube's public oEmbed service."""

    def __init__(self, timeout: float = _DEFAULT_TIMEOUT) -> None:
        self._timeout = timeout

    async def get_metadata(self, video_id: VideoId) -> tuple[str, str]:
        """Fetch title and channel for the given video ID.

        Falls back safely to default identifiers if the request fails or is timed out.
        """
        fallback_title = f"YouTube Video {video_id.value}"
        fallback_channel = "Canal Desconhecido"

        url = f"https://www.youtube.com/watch?v={video_id.value}"
        params = {"url": url, "format": "json"}

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(_OEMBED_URL, params=params)
                response.raise_for_status()
                data = response.json()

                title = data.get("title", fallback_title)
                channel = data.get("author_name", fallback_channel)
                return str(title), str(channel)

        except (httpx.HTTPError, Exception) as exc:
            logger.warning(
                "Failed to fetch oEmbed metadata for video %s: %s. Using fallback.",
                video_id.value,
                exc,
            )
            return fallback_title, fallback_channel
