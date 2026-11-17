"""YouTube Video ID Value Object."""

import re
from dataclasses import dataclass

from rhandir.core.domain.exceptions import InvalidVideoIdError

_YOUTUBE_ID_REGEX = re.compile(r"^[0-9A-Za-z_-]{11}$")


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

    def to_url(self) -> str:
        """Return the canonical YouTube watch URL."""
        return f"https://www.youtube.com/watch?v={self.value}"

    def __str__(self) -> str:
        return self.value
