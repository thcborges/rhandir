"""Daemon Controller for background ingestion service."""

import asyncio
import logging
import signal
from typing import Any

from rhandir.application.use_cases.ingest_history import IngestYouTubeHistoryUseCase

logger = logging.getLogger(__name__)


class DaemonController:
    """Manages the background execution loop, polling intervals, and graceful shutdown."""

    def __init__(
        self,
        history_use_case: IngestYouTubeHistoryUseCase,
        poll_interval_seconds: int = 60,
    ) -> None:
        self._history_use_case = history_use_case
        self._poll_interval = poll_interval_seconds
        self._running = False
        self._stop_event = asyncio.Event()

    def _setup_signal_handlers(self) -> None:
        """Register signal handlers for graceful termination."""
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self.stop)
            except (NotImplementedError, RuntimeError):
                # Signals might not be addable in certain test harnesses or Windows
                pass

    def stop(self, *args: Any) -> None:
        """Signal the daemon loop to stop gracefully."""
        logger.info("Received termination signal. Initiating graceful shutdown...")
        self._running = False
        self._stop_event.set()

    async def run(self) -> None:
        """Execute the continuous background daemon loop."""
        self._running = True
        self._stop_event.clear()
        self._setup_signal_handlers()

        logger.info("Rhandir daemon started. Poll interval: %ds", self._poll_interval)

        while self._running:
            try:
                summary = await self._history_use_case.execute()
                logger.info(
                    "Cycle finished: %d discovered, %d completed, %d no_transcript, %d failed.",
                    summary.total_discovered,
                    summary.completed,
                    summary.no_transcript,
                    summary.failed,
                )
            except Exception as exc:
                logger.error("Error during ingestion cycle: %s", exc, exc_info=True)

            # Cooperative non-blocking sleep that wakes immediately on stop event
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self._poll_interval)
            except TimeoutError:
                # Normal timeout: proceed to next cycle
                pass

        logger.info("Rhandir daemon terminated gracefully.")
