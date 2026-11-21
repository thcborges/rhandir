"""Unit tests for TelegramListener adapter.

BDD Specifications:
- Given an authorized Telegram message containing a YouTube URL,
  When processed by TelegramListener,
  Then:
    1. It immediately replies with an acknowledgment quoting the message and stating the link.
    2. At the end of processing, it replies with detailed completion status including vault path.

- Given a video that yields NO_TRANSCRIPT status,
  When processed by TelegramListener,
  Then:
    1. It acknowledges receipt quoting the message and stating the link.
    2. At the end, it replies with detailed status explaining that no subtitles are available.

- Given a video that yields FAILED status,
  When processed by TelegramListener,
  Then:
    1. It acknowledges receipt quoting the message and stating the link.
    2. At the end, it replies with detailed failure status, the error message, and what caused it.

- Given an unexpected exception during execution,
  When processed by TelegramListener,
  Then:
    1. It replies with detailed error information explaining what failed and the root cause.

- Given a message from an unauthorized chat ID,
  When processed by TelegramListener,
  Then it rejects the message and does not invoke the use case.

- Given a message without any YouTube link,
  When processed by TelegramListener,
  Then it replies quoting the message and informing that no valid link was found.

- Given /start or /help command,
  When processed by TelegramListener,
  Then it sends welcome instructions quoting the command.
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
def mock_metadata_provider() -> AsyncMock:
    provider = AsyncMock()
    provider.get_metadata.return_value = ("Rick Astley - Never Gonna Give You Up", "Rick Astley")
    return provider


@pytest.fixture
def mock_message() -> MagicMock:
    msg = MagicMock()
    msg.chat = MagicMock(id=123456)
    msg.text = "Olha esse vídeo: https://www.youtube.com/watch?v=dQw4w9WgXcQ recomendo!"
    msg.caption = None
    msg.reply = AsyncMock()
    return msg


@pytest.mark.asyncio
async def test_given_authorized_youtube_link_when_processing_then_acknowledges_and_reports_details(
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

    # Must send at least 2 messages: acknowledgment, then final status
    assert mock_message.reply.call_count == 2

    # 1. First message: Acknowledgment citing the received message and informing the link
    first_reply = mock_message.reply.call_args_list[0][0][0]
    assert "Confirmação de Recebimento" in first_reply
    assert mock_message.text in first_reply  # quotes original message
    assert "https://www.youtube.com/watch?v=dQw4w9WgXcQ" in first_reply

    # 2. Second message: Detailed final status
    final_reply = mock_message.reply.call_args_list[1][0][0]
    assert "Status do Processamento: Concluído com Sucesso" in final_reply
    assert "dQw4w9WgXcQ" in final_reply
    assert "/vault/note.md" in final_reply


@pytest.mark.asyncio
async def test_given_video_without_transcript_when_processing_then_acknowledges_and_reports_details(
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
        title="Instrumental",
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
    assert mock_message.reply.call_count == 2
    first_reply = mock_message.reply.call_args_list[0][0][0]
    assert "Confirmação de Recebimento" in first_reply
    assert "https://www.youtube.com/watch?v=dQw4w9WgXcQ" in first_reply

    final_reply = mock_message.reply.call_args_list[1][0][0]
    assert "Status do Processamento: Sem Transcrição" in final_reply
    assert "/vault/no_sub.md" in final_reply
    assert "não possui legendas" in final_reply


@pytest.mark.asyncio
async def test_given_video_failure_when_processing_then_acknowledges_and_reports_cause(
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
    failed_record.mark_failed(error_message="HTTP 429: Too Many Requests from YouTube")
    mock_video_use_case.execute.return_value = failed_record

    # When
    await listener.handle_message(mock_message)

    # Then
    assert mock_message.reply.call_count == 2
    first_reply = mock_message.reply.call_args_list[0][0][0]
    assert "Confirmação de Recebimento" in first_reply

    final_reply = mock_message.reply.call_args_list[1][0][0]
    assert "Status do Processamento: Falha" in final_reply
    assert "HTTP 429: Too Many Requests from YouTube" in final_reply
    assert "Causa do erro:" in final_reply


@pytest.mark.asyncio
async def test_given_unexpected_exception_when_processing_then_reports_error_and_cause(
    mock_video_use_case: AsyncMock,
    mock_repository: AsyncMock,
    mock_message: MagicMock,
) -> None:
    # Given: use case raises an unexpected error
    listener = TelegramListener(
        token="FAKE_TOKEN",
        video_use_case=mock_video_use_case,
        repository=mock_repository,
        allowed_chat_ids=[123456],
    )
    mock_video_use_case.execute.side_effect = RuntimeError("Database connection lost")

    # When
    await listener.handle_message(mock_message)

    # Then
    assert mock_message.reply.call_count == 2
    final_reply = mock_message.reply.call_args_list[1][0][0]
    assert "Status do Processamento: Falha Inesperada" in final_reply
    assert "Database connection lost" in final_reply
    assert "Causa do erro:" in final_reply


@pytest.mark.asyncio
async def test_given_unauthorized_chat_when_processing_then_rejects(
    mock_video_use_case: AsyncMock,
    mock_repository: AsyncMock,
    mock_message: MagicMock,
) -> None:
    # Given
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
async def test_given_text_without_link_when_processing_then_cites_and_prompts_user(
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
    assert "Olá bot, bom dia!" in reply_text
    assert "Nenhum link válido" in reply_text


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


@pytest.mark.asyncio
async def test_given_youtube_link_when_processing_then_fetches_real_metadata_for_vault_and_replies(
    mock_video_use_case: AsyncMock,
    mock_repository: AsyncMock,
    mock_metadata_provider: AsyncMock,
    mock_message: MagicMock,
) -> None:
    # Given
    listener = TelegramListener(
        token="FAKE_TOKEN",
        video_use_case=mock_video_use_case,
        repository=mock_repository,
        metadata_provider=mock_metadata_provider,
        allowed_chat_ids=[123456],
    )
    video = Video(
        video_id=VideoId("dQw4w9WgXcQ"),
        title="Rick Astley - Never Gonna Give You Up",
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
    mock_metadata_provider.get_metadata.assert_called_once_with(VideoId("dQw4w9WgXcQ"))
    saved_video = mock_repository.save_discovered.call_args[0][0]
    assert saved_video.title == "Rick Astley - Never Gonna Give You Up"
    assert saved_video.channel == "Rick Astley"
    assert saved_video.url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    final_reply = mock_message.reply.call_args_list[1][0][0]
    assert "Rick Astley - Never Gonna Give You Up" in final_reply
    assert "Rick Astley" in final_reply
