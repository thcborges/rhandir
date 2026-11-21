"""Unit tests for Rhandir CLI commands and container wiring."""

from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from rhandir.application.dtos.video_dto import IngestionSummaryDTO
from rhandir.cli.app import build_container, cli
from rhandir.infrastructure.config.settings import Settings
from rhandir.infrastructure.external.telegram_listener import TelegramListener

runner = CliRunner()


def test_cli_status_command() -> None:
    # Given
    mock_pool = MagicMock()
    mock_repo = AsyncMock()
    mock_repo.get_status_counts.return_value = {
        "completed": 10,
        "no_transcript": 2,
        "pending": 1,
        "failed": 0,
    }

    with (
        patch("rhandir.cli.app.create_db_pool", new_callable=AsyncMock, return_value=mock_pool),
        patch("rhandir.cli.app.close_db_pool", new_callable=AsyncMock),
        patch("rhandir.cli.app.PostgresIngestionRepository", return_value=mock_repo),
    ):
        # When
        result = runner.invoke(cli, ["status"])

        # Then
        assert result.exit_code == 0
        assert "completed" in result.output
        assert "10" in result.output


def test_cli_sync_youtube_command() -> None:
    # Given
    mock_pool = MagicMock()
    mock_repo = AsyncMock()
    mock_summary = IngestionSummaryDTO(
        total_discovered=5,
        newly_discovered=2,
        completed=2,
        no_transcript=0,
        failed=0,
        skipped_duplicates=3,
    )

    with (
        patch("rhandir.cli.app.create_db_pool", new_callable=AsyncMock, return_value=mock_pool),
        patch("rhandir.cli.app.close_db_pool", new_callable=AsyncMock),
        patch("rhandir.cli.app.PostgresIngestionRepository", return_value=mock_repo),
        patch(
            "rhandir.cli.app.IngestYouTubeHistoryUseCase.execute",
            new_callable=AsyncMock,
            return_value=mock_summary,
        ),
    ):
        # When
        result = runner.invoke(cli, ["sync", "youtube"])

        # Then
        assert result.exit_code == 0
        assert "Sincronização concluída com sucesso" in result.output
        assert "total_discovered=5" in result.output


def test_cli_sync_vault_command() -> None:
    # Given
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        # When
        result = runner.invoke(cli, ["sync", "vault", "--direction", "pull"])

        # Then
        assert result.exit_code == 0
        assert "Sincronização do Obsidian Vault concluída" in result.output
        mock_run.assert_called_once()


def test_given_telegram_token_when_building_container_then_wires_listener() -> None:
    settings = Settings(telegram_bot_token="FAKE_TOKEN:123456", telegram_allowed_chat_ids=[123])
    mock_pool = MagicMock()

    container = build_container(settings, mock_pool)

    assert container.message_listener is not None
    assert isinstance(container.message_listener, TelegramListener)
    assert container.daemon_controller._message_listener is container.message_listener


def test_given_no_telegram_token_when_building_container_then_listener_is_none() -> None:
    settings = Settings(telegram_bot_token=None)
    mock_pool = MagicMock()

    container = build_container(settings, mock_pool)

    assert container.message_listener is None
    assert container.daemon_controller._message_listener is None
