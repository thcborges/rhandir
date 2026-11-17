"""YouTube Transcript API Adapter.

Encapsulates the youtube-transcript-api library behind the domain ITranscriptProvider port,
offloading synchronous network requests to thread pools via asyncio.to_thread to maintain 100%
non-blocking event loop execution.
"""

import asyncio
from collections.abc import Sequence

from youtube_transcript_api import (
    IpBlocked,
    NoTranscriptFound,
    RequestBlocked,
    TranscriptsDisabled,
    VideoUnavailable,
    VideoUnplayable,
    YouTubeTranscriptApi,
)

from rhandir.core.domain.exceptions import (
    CollectorError,
    RateLimitExceededError,
    TranscriptNotFoundError,
)
from rhandir.core.domain.value_objects.video_id import VideoId
from rhandir.core.ports.transcripts import ITranscriptProvider


class YouTubeTranscriptProvider(ITranscriptProvider):
    """Fetches and cleans transcripts using youtube-transcript-api."""

    def __init__(
        self,
        languages: Sequence[str] = ("pt", "pt-BR", "en"),
        api: YouTubeTranscriptApi | None = None,
    ) -> None:
        self._languages = tuple(languages)
        self._api = api or YouTubeTranscriptApi()

    def _group_into_paragraphs(self, snippets: list[str]) -> list[str]:
        """Aggregate short transcript snippets into coherent paragraphs."""
        paragraphs: list[str] = []
        current_chunk: list[str] = []
        current_len = 0

        for text in snippets:
            clean = text.strip().replace("\n", " ")
            if not clean:
                continue

            current_chunk.append(clean)
            current_len += len(clean)

            # Split on terminal punctuation or length threshold
            if (clean.endswith((".", "!", "?")) and current_len >= 250) or current_len >= 500:
                paragraphs.append(" ".join(current_chunk))
                current_chunk = []
                current_len = 0

        if current_chunk:
            paragraphs.append(" ".join(current_chunk))

        return paragraphs

    def _fetch_sync(self, vid_str: str) -> list[str]:
        """Synchronously fetch transcript snippets."""
        try:
            transcript = self._api.fetch(vid_str, languages=self._languages)
            raw_snippets = [snippet.text for snippet in transcript]
            return self._group_into_paragraphs(raw_snippets)
        except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable, VideoUnplayable) as exc:
            msg = f"No transcript available for video {vid_str}: {exc}"
            raise TranscriptNotFoundError(msg) from exc
        except (IpBlocked, RequestBlocked) as exc:
            msg = f"YouTube rate limit/IP block detected for video {vid_str}: {exc}"
            raise RateLimitExceededError(msg) from exc
        except Exception as exc:
            msg = f"Failed to retrieve transcript for video {vid_str}: {exc}"
            raise CollectorError(msg) from exc

    async def get_transcript(self, video_id: VideoId) -> list[str]:
        """Asynchronously retrieve and format transcript into clean paragraphs."""
        return await asyncio.to_thread(self._fetch_sync, video_id.value)
