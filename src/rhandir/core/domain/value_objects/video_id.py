"""YouTube Video ID Value Object."""

import re
from dataclasses import dataclass

from rhandir.core.domain.exceptions import InvalidVideoIdError

_YOUTUBE_ID_REGEX = re.compile(r"^[0-9A-Za-z_-]{11}$")

_YOUTUBE_URL_EXTRACT_REGEX = re.compile(
    r"(?:https?://)?(?:www\.|m\.)?(?:"
    r"youtu\.be/([0-9A-Za-z_-]{11})|"
    r"youtube\.com/(?:shorts/|live/|embed/)([0-9A-Za-z_-]{11})|"
    r"youtube\.com/watch\?[^\s]*?[?&]v=([0-9A-Za-z_-]{11})|"
    r"youtube\.com/watch\?v=([0-9A-Za-z_-]{11})"
    r")(?![0-9A-Za-z_-])",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class VideoId:
    """Immutable Value Object representing a YouTube video ID."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not _YOUTUBE_ID_REGEX.match(self.value):
            msg = (
                f"Invalid YouTube video ID: '{self.value}'. "
                "Expected 11 alphanumeric characters, dashes, or underscores."
            )
            raise InvalidVideoIdError(msg)

    @classmethod
    def extract_from_text(cls, text: str) -> "VideoId | None":
        """Extract the first valid YouTube VideoId found in arbitrary text or URL."""
        if not text:
            return None
        match = _YOUTUBE_URL_EXTRACT_REGEX.search(text)
        if not match:
            return None
        raw_id = match.group(1) or match.group(2) or match.group(3) or match.group(4)
        if not raw_id:
            return None
        try:
            return cls(raw_id)
        except InvalidVideoIdError:
            return None

    def to_url(self) -> str:
        """Return the canonical YouTube watch URL."""
        return f"https://www.youtube.com/watch?v={self.value}"

    def __str__(self) -> str:
        return self.value
