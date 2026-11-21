"""Unit tests for YouTube Video ID extraction from text and messages.

BDD Specifications:
- Given a text message with a standard YouTube watch URL,
  When extracting VideoId from text,
  Then it returns the valid VideoId value object.

- Given a text message with a short youtu.be URL,
  When extracting VideoId from text,
  Then it returns the valid VideoId value object.

- Given a text message with a YouTube shorts or live URL,
  When extracting VideoId from text,
  Then it returns the valid VideoId value object.

- Given a text message with query parameters (timestamps, tracking),
  When extracting VideoId from text,
  Then query parameters are ignored and the pure 11-char VideoId is returned.

- Given a text message without any YouTube link or with invalid links,
  When extracting VideoId from text,
  Then it returns None safely without raising exceptions.
"""

import pytest

from rhandir.core.domain.value_objects.video_id import VideoId


@pytest.mark.parametrize(
    ("message_text", "expected_id"),
    [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/live/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        (
            "Confira este vídeo: https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120s muito bom!",
            "dQw4w9WgXcQ",
        ),
        (
            "Veja aqui https://youtu.be/dQw4w9WgXcQ?si=abcdef123456",
            "dQw4w9WgXcQ",
        ),
        ("Acesse https://youtu.be/a1B2c3D4e5F", "a1B2c3D4e5F"),
    ],
)
def test_given_text_with_youtube_link_when_extracting_then_returns_video_id(
    message_text: str, expected_id: str
) -> None:
    # When
    result = VideoId.extract_from_text(message_text)

    # Then
    assert result is not None
    assert result.value == expected_id


@pytest.mark.parametrize(
    "invalid_text",
    [
        "",
        "Olá, tudo bem?",
        "https://vimeo.com/12345678",
        "https://google.com/search?q=youtube",
        "https://youtube.com/channel/UCuAXFkgsw1L7xaCfnd5JJOw",
        "https://youtu.be/short",
        "https://www.youtube.com/watch?v=toolongidhere123456",
    ],
)
def test_given_text_without_youtube_video_when_extracting_then_returns_none(
    invalid_text: str,
) -> None:
    # When
    result = VideoId.extract_from_text(invalid_text)

    # Then
    assert result is None
