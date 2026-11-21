"""Port for fetching video metadata (title, channel)."""

from typing import Protocol

from rhandir.core.domain.value_objects.video_id import VideoId


class IVideoMetadataProvider(Protocol):
    """Port for retrieving external video metadata."""

    async def get_metadata(self, video_id: VideoId) -> tuple[str, str]:
        """Fetch title and channel for a video ID.

        Returns:
            tuple[str, str]: (title, channel)
        """
        ...
