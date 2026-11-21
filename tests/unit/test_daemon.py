"""Unit tests for DaemonController."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from rhandir.application.dtos.video_dto import IngestionSummaryDTO
from rhandir.interfaces.controllers.daemon import DaemonController


@pytest.mark.asyncio
async def test_given_daemon_controller_when_running_then_executes_cycle_and_stops() -> None:
    # Given
    mock_use_case = AsyncMock()
    mock_use_case.execute.return_value = IngestionSummaryDTO(
        total_discovered=1,
        newly_discovered=1,
        completed=1,
        no_transcript=0,
        failed=0,
        skipped_duplicates=0,
    )

    controller = DaemonController(
        history_use_case=mock_use_case,
        poll_interval_seconds=1,
    )

    # When: Start daemon in background and stop it after a tiny delay
    task = asyncio.create_task(controller.run())
    await asyncio.sleep(0.05)
    controller.stop()
    await task

    # Then
    mock_use_case.execute.assert_called()
    assert not controller._running


@pytest.mark.asyncio
async def test_given_daemon_with_listener_when_running_then_manages_lifecycle() -> None:
    # Given
    mock_use_case = AsyncMock()
    mock_use_case.execute.return_value = IngestionSummaryDTO(
        total_discovered=0,
        newly_discovered=0,
        completed=0,
        no_transcript=0,
        failed=0,
        skipped_duplicates=0,
    )
    mock_listener = AsyncMock()

    controller = DaemonController(
        history_use_case=mock_use_case,
        message_listener=mock_listener,
        poll_interval_seconds=1,
    )

    # When: Start daemon in background and stop it after a tiny delay
    task = asyncio.create_task(controller.run())
    await asyncio.sleep(0.05)
    controller.stop()
    await task

    # Then
    mock_listener.start.assert_called_once()
    mock_listener.stop.assert_called_once()
