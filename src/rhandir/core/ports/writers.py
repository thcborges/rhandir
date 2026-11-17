"""Core Vault Writer Port."""

from typing import Protocol

from rhandir.core.domain.entities.video import Video
from rhandir.core.domain.value_objects.status import IngestionStatus


class IVaultWriter(Protocol):
    """Abstract port for generating and writing Markdown notes into the Obsidian vault."""

    async def write_note(
        self,
        video: Video,
        transcript_paragraphs: list[str] | None,
        status: IngestionStatus,
    ) -> str:
        """Atomically write formatted Markdown note to the raw directory.

        Returns:
            The absolute path of the generated note file.

        Raises:
            VaultWriteError: If writing to the file system fails.
        """
        ...
