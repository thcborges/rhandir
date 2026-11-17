"""Core History Collector Port."""

from typing import Protocol

from rhandir.core.domain.entities.video import Video


class IHistoryCollector(Protocol):
    """Abstract port for collecting watch history from external sources."""

    async def collect_history(self) -> list[Video]:
        """Collect and parse watch history entries into domain Video entities."""
        ...
