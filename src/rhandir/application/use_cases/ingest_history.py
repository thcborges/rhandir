"""Use case for processing a batch of YouTube watch history entries."""

import logging

from rhandir.application.dtos.video_dto import IngestionSummaryDTO
from rhandir.application.services.circuit_breaker import CircuitBreaker
from rhandir.application.use_cases.ingest_video import IngestYouTubeVideoUseCase
from rhandir.core.domain.value_objects.status import IngestionStatus
from rhandir.core.ports.collectors import IHistoryCollector
from rhandir.core.ports.repositories import IIngestionRepository

logger = logging.getLogger(__name__)


class IngestYouTubeHistoryUseCase:
    """Orchestrates scanning watch history, deduplicating, and sequential ingestion."""

    def __init__(
        self,
        collector: IHistoryCollector,
        repository: IIngestionRepository,
        video_use_case: IngestYouTubeVideoUseCase,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self._collector = collector
        self._repository = repository
        self._video_use_case = video_use_case
        self._circuit_breaker = circuit_breaker or CircuitBreaker()

    async def execute(self, max_items: int = 100) -> IngestionSummaryDTO:
        """Scan history source, discover new videos, and ingest pending items."""
        logger.info("Scanning YouTube history collector...")
        discovered_videos = await self._collector.collect_history()
        total_discovered = len(discovered_videos)

        newly_discovered = 0
        skipped_duplicates = 0

        # Phase 1: Deduplication and registration
        for video in discovered_videos:
            exists = await self._repository.exists(video.video_id)
            if not exists:
                await self._repository.save_discovered(video)
                newly_discovered += 1
            else:
                skipped_duplicates += 1

        logger.info(
            "History scan complete: %d total, %d newly registered, %d skipped duplicates.",
            total_discovered,
            newly_discovered,
            skipped_duplicates,
        )

        # Phase 2: Sequential processing of pending videos
        pending_videos = await self._repository.get_pending_videos(limit=max_items)
        completed = 0
        no_transcript = 0
        failed = 0

        for video in pending_videos:
            # Check circuit breaker before processing
            if self._circuit_breaker.is_tripped():
                logger.warning("Circuit breaker is tripped. Pausing history batch processing.")
                break

            record = await self._video_use_case.execute(video)
            if record.status == IngestionStatus.COMPLETED:
                completed += 1
            elif record.status == IngestionStatus.NO_TRANSCRIPT:
                no_transcript += 1
            elif record.status == IngestionStatus.FAILED:
                failed += 1

        return IngestionSummaryDTO(
            total_discovered=total_discovered,
            newly_discovered=newly_discovered,
            completed=completed,
            no_transcript=no_transcript,
            failed=failed,
            skipped_duplicates=skipped_duplicates,
        )
