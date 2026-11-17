"""Core Domain Exceptions.

Pure business exceptions independent of any external frameworks.
"""


class DomainError(Exception):
    """Base class for all domain exceptions in rhandir."""

    pass


class InvalidVideoIdError(DomainError):
    """Raised when a video ID does not adhere to canonical format constraints."""

    pass


class TranscriptNotFoundError(DomainError):
    """Raised when no subtitles or transcripts are available for a video."""

    pass


class RateLimitExceededError(DomainError):
    """Raised when a rate limit (HTTP 429 / Captcha) is encountered."""

    pass


class VaultWriteError(DomainError):
    """Raised when writing to the Obsidian vault raw folder fails."""

    pass


class CollectorError(DomainError):
    """Raised when history collection fails."""

    pass
