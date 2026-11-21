"""Unit tests for TelegramListener adapter.

BDD Specifications:
- Given an authorized Telegram message containing a YouTube URL,
  When processed by TelegramListener,
  Then it registers the video, invokes IngestYouTubeVideoUseCase, and replies with success.

- Given a message from an unauthorized chat ID,
  When processed by TelegramListener,
  Then it rejects the message and does not invoke the use case.

- Given a message without any YouTube link,
  When processed by TelegramListener,
  Then it informs the user and does not invoke the use case.

- Given a video that yields NO_TRANSCRIPT status,
  When processed by TelegramListener,
  Then it replies with a warning and informs the vault path.

- Given a video that yields FAILED status,
  When processed by TelegramListener,
  Then it replies reporting the failure reason.

- Given TelegramListener lifecycle,
  When start and stop are invoked,
  Then polling and bot session are managed gracefully.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from rhandir.core.domain.entities.video import IngestionRecord, Video
from rhandir.core.domain.value_objects.video_id import VideoId
from rhandir.infrastructure.external.telegram_listener import TelegramListener


@pytest.fixture
def mock_video_use_case() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_message() -> MagicMock:
    msg = MagicMock()
    msg.chat = MagicMock(id=123456)
    msg.text = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    msg.caption = None
    msg.reply = AsyncMock()
    return msg


@pytest.mark.asyncio
async def test_given_authorized_youtube_link_when_processing_then_ingests_and_replies_success(
    mock_video_use_case: AsyncMock,
    mock_repository: AsyncMock,
    mock_message: MagicMock,
) -> None:
    # Given
    listener = TelegramListener(
        token="FAKE_TOKEN",
        video_use_case=mock_video_use_case,
        repository=mock_repository,
        allowed_chat_ids=[123456],
    )
    video = Video(
        video_id=VideoId("dQw4w9WgXcQ"),
        title="Never Gonna Give You Up",
        channel="Rick Astley",
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        watched_at=None,
        discovered_at=MagicMock(),
    )
    completed_record = IngestionRecord.create_pending(video)
    completed_record.mark_completed(vault_path="/vault/note.md")
    mock_video_use_case.execute.return_value = completed_record

    # When
    await listener.handle_message(mock_message)

    # Then
    mock_repository.save_discovered.assert_called_once()
    mock_video_use_case.execute.assert_called_once()
    assert mock_message.reply.call_count >= 1
    last_reply = mock_message.reply.call_args[0][0]
    assert "Transcrição salva com sucesso" in last_reply
    assert "/vault/note.md" in last_reply


@pytest.mark.asyncio
async def test_given_unauthorized_chat_when_processing_then_rejects(
    mock_video_use_case: AsyncMock,
    mock_repository: AsyncMock,
    mock_message: MagicMock,
) -> None:
    # Given: allowed chats don't include message.chat.id (123456)
    listener = TelegramListener(
        token="FAKE_TOKEN",
        video_use_case=mock_video_use_case,
        repository=mock_repository,
        allowed_chat_ids=[999999],
    )

    # When
    await listener.handle_message(mock_message)

    # Then
    mock_video_use_case.execute.assert_not_called()
    mock_repository.save_discovered.assert_not_called()
    mock_message.reply.assert_called_once()
    reply_text = mock_message.reply.call_args[0][0]
    assert "não autorizado" in reply_text.lower()


@pytest.mark.asyncio
async def test_given_text_without_link_when_processing_then_prompts_user(
    mock_video_use_case: AsyncMock,
    mock_repository: AsyncMock,
    mock_message: MagicMock,
) -> None:
    # Given
    mock_message.text = "Olá bot, bom dia!"
    listener = TelegramListener(
        token="FAKE_TOKEN",
        video_use_case=mock_video_use_case,
        repository=mock_repository,
        allowed_chat_ids=[123456],
    )

    # When
    await listener.handle_message(mock_message)

    # Then
    mock_video_use_case.execute.assert_not_called()
    mock_repository.save_discovered.assert_not_called()
    mock_message.reply.assert_called_once()
    reply_text = mock_message.reply.call_args[0][0]
    assert "Nenhum link válido" in reply_text


@pytest.mark.asyncio
async def test_given_video_without_transcript_when_processing_then_informs_no_transcript(
    mock_video_use_case: AsyncMock,
    mock_repository: AsyncMock,
    mock_message: MagicMock,
) -> None:
    # Given
    listener = TelegramListener(
        token="FAKE_TOKEN",
        video_use_case=mock_video_use_case,
        repository=mock_repository,
        allowed_chat_ids=[123456],
    )
    video = Video(
        video_id=VideoId("dQw4w9WgXcQ"),
        title="Test Video",
        channel="Channel",
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        watched_at=None,
        discovered_at=MagicMock(),
    )
    no_sub_record = IngestionRecord.create_pending(video)
    no_sub_record.mark_no_transcript(vault_path="/vault/no_sub.md")
    mock_video_use_case.execute.return_value = no_sub_record

    # When
    await listener.handle_message(mock_message)

    # Then
    last_reply = mock_message.reply.call_args[0][0]
    assert "não possui legendas disponíveis" in last_reply
    assert "/vault/no_sub.md" in last_reply


@pytest.mark.asyncio
async def test_given_video_failure_when_processing_then_reports_error(
    mock_video_use_case: AsyncMock,
    mock_repository: AsyncMock,
    mock_message: MagicMock,
) -> None:
    # Given
    listener = TelegramListener(
        token="FAKE_TOKEN",
        video_use_case=mock_video_use_case,
        repository=mock_repository,
        allowed_chat_ids=[123456],
    )
    video = Video(
        video_id=VideoId("dQw4w9WgXcQ"),
        title="Test Video",
        channel="Channel",
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        watched_at=None,
        discovered_at=MagicMock(),
    )
    failed_record = IngestionRecord.create_pending(video)
    failed_record.mark_failed(error_message="HTTP 429 Too Many Requests")
    mock_video_use_case.execute.return_value = failed_record

    # When
    await listener.handle_message(mock_message)

    # Then
    last_reply = mock_message.reply.call_args[0][0]
    assert "Falha ao processar vídeo" in last_reply
    assert "HTTP 429 Too Many Requests" in last_reply


@pytest.mark.asyncio
async def test_given_start_command_when_processing_then_sends_welcome_guide(
    mock_video_use_case: AsyncMock,
    mock_repository: AsyncMock,
    mock_message: MagicMock,
) -> None:
    # Given
    mock_message.text = "/start"
    listener = TelegramListener(
        token="FAKE_TOKEN",
        video_use_case=mock_video_use_case,
        repository=mock_repository,
        allowed_chat_ids=[123456],
    )

    # When
    await listener.handle_message(mock_message)

    # Then
    mock_message.reply.assert_called_once()
    reply_text = mock_message.reply.call_args[0][0]
    assert "Envie um link de vídeo do YouTube" in reply_text


@pytest.mark.asyncio
async def test_given_mocked_bot_and_dp_when_starting_and_stopping_then_handles_lifecycle(
    mock_video_use_case: AsyncMock,
    mock_repository: AsyncMock,
) -> None:
    mock_bot = MagicMock()
    mock_bot.session = AsyncMock()
    mock_dp = MagicMock()
    mock_dp.start_polling = AsyncMock()
    mock_dp.stop_polling = AsyncMock()

    listener = TelegramListener(
        token="FAKE_TOKEN",
        video_use_case=mock_video_use_case,
        repository=mock_repository,
        bot=mock_bot,
        dp=mock_dp,
    )

    await listener.start()
    assert listener._polling_task is not None

    await listener.stop()
    mock_dp.stop_polling.assert_called_once()
    mock_bot.session.close.assert_called_once()


@pytest.mark.asyncio
async def test_given_empty_token_when_start_then_does_nothing(
    mock_video_use_case: AsyncMock,
    mock_repository: AsyncMock,
) -> None:
    listener = TelegramListener(
        token="",
        video_use_case=mock_video_use_case,
        repository=mock_repository,
    )
    await listener.start()
    assert listener._polling_task is None
