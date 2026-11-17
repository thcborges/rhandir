"""Vault Writer Filesystem Adapter."""

import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

import aiofiles

from rhandir.core.domain.entities.video import Video
from rhandir.core.domain.exceptions import VaultWriteError
from rhandir.core.domain.value_objects.status import IngestionStatus
from rhandir.core.ports.writers import IVaultWriter
from rhandir.interfaces.presenters.markdown_presenter import MarkdownPresenter


class VaultWriter(IVaultWriter):
    """Writes Markdown notes atomically into the Obsidian raw directory using async I/O."""

    def __init__(
        self,
        output_dir: Path | str,
        presenter: MarkdownPresenter | None = None,
    ) -> None:
        self._output_dir = Path(output_dir)
        self._presenter = presenter or MarkdownPresenter()

    async def write_note(
        self,
        video: Video,
        transcript_paragraphs: list[str] | None,
        status: IngestionStatus,
    ) -> str:
        """Atomically write formatted Markdown note to the raw directory."""
        try:
            self._output_dir.mkdir(parents=True, exist_ok=True)
            filename = self._presenter.format_filename(video)
            target_path = self._output_dir / filename

            # Write to a unique temporary file in the same filesystem directory
            temp_filename = f".tmp_{filename}_{uuid.uuid4().hex}"
            temp_path = self._output_dir / temp_filename

            content = self._presenter.format_note(
                video=video,
                transcript_paragraphs=transcript_paragraphs,
                status=status,
                ingested_at=datetime.now(UTC),
            )

            async with aiofiles.open(temp_path, mode="w", encoding="utf-8") as f:
                await f.write(content)

            # Atomic swap to guarantee crash safety
            os.replace(temp_path, target_path)
            return str(target_path.resolve())

        except OSError as exc:
            msg = f"Failed to write note for video {video.video_id}: {exc}"
            raise VaultWriteError(msg) from exc
