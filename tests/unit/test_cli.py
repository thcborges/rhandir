"""Unit tests for Rhandir CLI commands."""

from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from rhandir.application.dtos.video_dto import IngestionSummaryDTO
from rhandir.cli.app import cli

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
