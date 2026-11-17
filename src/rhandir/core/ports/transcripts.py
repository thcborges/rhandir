"""Core Transcript Provider Port."""

from typing import Protocol

from rhandir.core.domain.value_objects.video_id import VideoId


class ITranscriptProvider(Protocol):
    """Abstract port for fetching subtitles/transcripts for a video."""

    async def get_transcript(self, video_id: VideoId) -> list[str]:
        """Fetch transcript lines or paragraphs for a given video ID.

        Raises:
            TranscriptNotFoundError: If no subtitles exist or are disabled.
            RateLimitExceededError: If HTTP 429 or bot blocking occurs.
        """
        ...
