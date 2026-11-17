"""Markdown and Frontmatter Presenter for Obsidian Vault."""

import re
from datetime import UTC, datetime

from rhandir.core.domain.entities.video import Video
from rhandir.core.domain.value_objects.status import IngestionStatus

_INVALID_CHARS_REGEX = re.compile(r'[/\\:*?"<>|\n\r\t]+')
_MULTIPLE_HYPHENS_REGEX = re.compile(r"(?:\s*-\s*){2,}")
_MULTIPLE_SPACES_REGEX = re.compile(r"\s+")


class MarkdownPresenter:
    """Formats domain Video entities and transcripts into Obsidian-compliant Markdown notes."""

    def sanitize_title(self, raw_title: str) -> str:
        """Sanitize video titles for safe YAML frontmatter and cross-platform filenames."""
        # Replace forbidden characters with a clean separator
        cleaned = _INVALID_CHARS_REGEX.sub(" - ", raw_title)
        # Collapse multiple hyphens or spaces
        cleaned = _MULTIPLE_SPACES_REGEX.sub(" ", cleaned)
        cleaned = _MULTIPLE_HYPHENS_REGEX.sub(" - ", cleaned)
        cleaned = cleaned.strip(" -")
        return cleaned or "Sem Titulo"

    def format_filename(self, video: Video) -> str:
        """Generate deterministic filename: YYYY-MM-DD - [Clean Title] - [ID].md."""
        date_ref = video.watched_at or video.discovered_at or datetime.now(UTC)
        date_str = date_ref.astimezone(UTC).strftime("%Y-%m-%d")
        clean_title = self.sanitize_title(video.title)
        # Truncate title if extremely long to avoid max path limit
        if len(clean_title) > 120:
            clean_title = clean_title[:120].rstrip(" -")
        return f"{date_str} - {clean_title} - {video.video_id}.md"

    def format_note(
        self,
        video: Video,
        transcript_paragraphs: list[str] | None,
        status: IngestionStatus,
        ingested_at: datetime | None = None,
    ) -> str:
        """Render complete Obsidian note with YAML frontmatter and transcript body."""
        timestamp = (ingested_at or datetime.now(UTC)).astimezone(UTC).isoformat()
        clean_title = self.sanitize_title(video.title)
        escaped_title = clean_title.replace('"', '\\"')
        escaped_channel = video.channel.replace('"', '\\"')

        frontmatter_status = "raw" if status == IngestionStatus.COMPLETED else "no_transcript"

        lines: list[str] = [
            "---",
            f'title: "{escaped_title}"',
            f'source_url: "{video.url}"',
            f'channel: "{escaped_channel}"',
            f'video_id: "{video.video_id}"',
            f'ingested_at: "{timestamp}"',
            f'status: "{frontmatter_status}"',
            'type: "youtube_video"',
            "tags:",
            "  - type/media/video",
            "  - source/youtube",
            f"  - status/{frontmatter_status}",
            "---",
            "",
            f"# {clean_title}",
            "",
            f"> **Canal:** [[{video.channel}]] | **Link:** [YouTube]({video.url})",
            "",
            "## Transcrição",
            "",
        ]

        if status == IngestionStatus.NO_TRANSCRIPT or not transcript_paragraphs:
            lines.extend(
                [
                    "> [!WARNING] Transcrição indisponível",
                    (
                        "> Este vídeo não possui legendas ou transcrições disponíveis "
                        "no YouTube no momento da ingestão."
                    ),
                    "",
                ]
            )
        else:
            for paragraph in transcript_paragraphs:
                cleaned_p = paragraph.strip()
                if cleaned_p:
                    lines.append(cleaned_p)
                    lines.append("")

        return "\n".join(lines)
