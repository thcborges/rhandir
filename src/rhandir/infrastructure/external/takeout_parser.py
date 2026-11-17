"""Google Takeout Watch History Parser and Collector."""

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from rhandir.core.domain.entities.video import Video
from rhandir.core.domain.exceptions import CollectorError, InvalidVideoIdError
from rhandir.core.domain.value_objects.video_id import VideoId
from rhandir.core.ports.collectors import IHistoryCollector

_PREFIX_REGEX = re.compile(
    r"^(?:Watched|Assistiu a|Assistiu ao|Has visto|Regardé|Angesehen)\s+",
    re.IGNORECASE,
)


class TakeoutParser:
    """Parses Google Takeout watch history files into domain Video entities."""

    def clean_title(self, raw_title: str) -> str:
        """Strip localization prefixes such as 'Watched ' or 'Assistiu a '."""
        return _PREFIX_REGEX.sub("", raw_title).strip()

    def extract_video_id(self, url: str) -> VideoId | None:
        """Extract valid 11-char VideoId from standard or shortened YouTube URLs."""
        if not url:
            return None
        try:
            parsed = urlparse(url)
            if "youtube.com" in parsed.netloc:
                qs = parse_qs(parsed.query)
                v_params = qs.get("v")
                if v_params and len(v_params[0]) == 11:
                    return VideoId(v_params[0])
            elif "youtu.be" in parsed.netloc:
                vid = parsed.path.strip("/")
                if len(vid) == 11:
                    return VideoId(vid)
        except (InvalidVideoIdError, ValueError):
            return None
        return None

    def parse_item(self, item: dict[str, Any], discovered_at: datetime) -> Video | None:
        """Transform a single Takeout entry into a Video entity."""
        title_url = item.get("titleUrl")
        if not title_url:
            return None

        video_id = self.extract_video_id(title_url)
        if not video_id:
            return None

        raw_title = item.get("title", "")
        clean_title = self.clean_title(raw_title)

        # Extract channel name
        channel = "Canal Desconhecido"
        subtitles = item.get("subtitles")
        if isinstance(subtitles, list) and len(subtitles) > 0:
            first_sub = subtitles[0]
            if isinstance(first_sub, dict) and "name" in first_sub:
                channel = first_sub["name"]

        # Parse watched_at
        watched_at = None
        time_str = item.get("time")
        if time_str:
            try:
                # Handle ISO timestamps with Z
                clean_time = time_str.replace("Z", "+00:00")
                watched_at = datetime.fromisoformat(clean_time)
            except ValueError:
                watched_at = None

        return Video(
            video_id=video_id,
            title=clean_title,
            channel=channel,
            url=video_id.to_url(),
            watched_at=watched_at,
            discovered_at=discovered_at,
        )

    def parse_file(self, file_path: Path | str) -> list[Video]:
        """Read and parse a JSON Takeout file."""
        path = Path(file_path)
        if not path.exists():
            raise CollectorError(f"Takeout file not found at: {path}")

        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            raise CollectorError(f"Failed to read/parse Takeout JSON from {path}: {exc}") from exc

        if not isinstance(data, list):
            raise CollectorError(f"Expected JSON list in {path}, got {type(data).__name__}")

        now = datetime.now(UTC)
        videos: list[Video] = []
        for entry in data:
            if isinstance(entry, dict):
                video = self.parse_item(entry, discovered_at=now)
                if video:
                    videos.append(video)

        return videos


class TakeoutCollector(IHistoryCollector):
    """Adapter monitoring the Takeout inbox folder for exported history files."""

    def __init__(
        self,
        inbox_dir: Path | str,
        parser: TakeoutParser | None = None,
    ) -> None:
        self._inbox_dir = Path(inbox_dir)
        self._parser = parser or TakeoutParser()

    async def collect_history(self) -> list[Video]:
        """Scan inbox folder for watch-history.json and return discovered videos."""
        if not self._inbox_dir.exists():
            self._inbox_dir.mkdir(parents=True, exist_ok=True)
            return []

        all_videos: list[Video] = []
        # Find JSON files
        for json_file in sorted(self._inbox_dir.glob("*.json")):
            videos = self._parser.parse_file(json_file)
            all_videos.extend(videos)

        return all_videos
