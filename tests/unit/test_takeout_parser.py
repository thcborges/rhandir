"""Unit tests for Google Takeout Watch History Parser and Collector.

BDD Specifications:
- Given a Takeout JSON file with watched videos,
  When TakeoutParser parses the data,
  Then it produces domain Video entities with sanitized titles and channels.

- Given a monitored folder with Takeout JSON files,
  When TakeoutCollector collects history,
  Then all JSON files are discovered and converted to domain Video entities.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from rhandir.infrastructure.external.takeout_parser import TakeoutCollector, TakeoutParser


def test_given_takeout_json_when_parsing_then_extracts_clean_videos(tmp_path: Path) -> None:
    # Given
    sample_data = [
        {
            "header": "YouTube",
            "title": "Watched Never Gonna Give You Up",
            "titleUrl": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "subtitles": [
                {
                    "name": "Rick Astley",
                    "url": "https://www.youtube.com/channel/UCuAXFkgsw1L7xaCfnd5JJOw",
                }
            ],
            "time": "2026-11-16T18:42:15.123Z",
        },
        {
            "header": "YouTube",
            "title": "Assistiu a Arquitetura Limpa na Prática",
            "titleUrl": "https://www.youtube.com/watch?v=abcdefghijk",
            "subtitles": [
                {
                    "name": "Canal Dev",
                    "url": "https://www.youtube.com/channel/123",
                }
            ],
            "time": "2026-11-15T10:00:00.000Z",
        },
        {
            # Ad entry or deleted video without URL
            "header": "YouTube",
            "title": "Visited an ad",
            "time": "2026-11-15T09:00:00.000Z",
        },
    ]

    takeout_file = tmp_path / "watch-history.json"
    takeout_file.write_text(json.dumps(sample_data), encoding="utf-8")

    # When
    parser = TakeoutParser()
    videos = parser.parse_file(takeout_file)

    # Then
    assert len(videos) == 2

    v1 = videos[0]
    assert v1.video_id.value == "dQw4w9WgXcQ"
    assert v1.title == "Never Gonna Give You Up"
    assert v1.channel == "Rick Astley"
    assert v1.url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert v1.watched_at == datetime(2026, 11, 16, 18, 42, 15, 123000, tzinfo=UTC)

    v2 = videos[1]
    assert v2.video_id.value == "abcdefghijk"
    assert v2.title == "Arquitetura Limpa na Prática"
    assert v2.channel == "Canal Dev"


@pytest.mark.asyncio
async def test_given_inbox_directory_when_collecting_history_then_returns_all_videos(
    tmp_path: Path,
) -> None:
    # Given
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    sample = [
        {
            "header": "YouTube",
            "title": "Watched Clean Architecture",
            "titleUrl": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "subtitles": [{"name": "Uncle Bob"}],
            "time": "2026-11-16T12:00:00Z",
        }
    ]
    (inbox / "history1.json").write_text(json.dumps(sample), encoding="utf-8")

    collector = TakeoutCollector(inbox_dir=inbox)

    # When
    videos = await collector.collect_history()

    # Then
    assert len(videos) == 1
    assert videos[0].video_id.value == "dQw4w9WgXcQ"
    assert videos[0].channel == "Uncle Bob"


@pytest.mark.asyncio
async def test_given_nested_subdirectories_when_collecting_history_then_returns_all_videos(
    tmp_path: Path,
) -> None:
    # Given
    inbox = tmp_path / "inbox"
    sub_dir = inbox / "YouTube e YouTube Music" / "histórico"
    sub_dir.mkdir(parents=True)
    sample = [
        {
            "header": "YouTube",
            "title": "Watched Clean Architecture",
            "titleUrl": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "subtitles": [{"name": "Uncle Bob"}],
            "time": "2026-11-16T12:00:00Z",
        }
    ]
    (sub_dir / "histórico-de-visualização.json").write_text(json.dumps(sample), encoding="utf-8")

    collector = TakeoutCollector(inbox_dir=inbox)

    # When
    videos = await collector.collect_history()

    # Then
    assert len(videos) == 1
    assert videos[0].video_id.value == "dQw4w9WgXcQ"
    assert videos[0].channel == "Uncle Bob"
