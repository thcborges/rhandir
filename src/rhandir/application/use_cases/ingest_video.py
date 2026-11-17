"""Use case for ingesting a single YouTube video."""

import logging

from rhandir.application.services.circuit_breaker import CircuitBreaker
from rhandir.core.domain.entities.video import IngestionRecord, Video
from rhandir.core.domain.exceptions import RateLimitExceededError, TranscriptNotFoundError
from rhandir.core.domain.value_objects.status import IngestionStatus
from rhandir.core.ports.repositories import IIngestionRepository
from rhandir.core.ports.transcripts import ITranscriptProvider
from rhandir.core.ports.writers import IVaultWriter

logger = logging.getLogger(__name__)


class IngestYouTubeVideoUseCase:
    """Orchestrates fetching transcript, writing Obsidian note, and updating DB status."""

    def __init__(
        self,
        transcript_provider: ITranscriptProvider,
        vault_writer: IVaultWriter,
        repository: IIngestionRepository,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self._transcript_provider = transcript_provider
        self._vault_writer = vault_writer
        self._repository = repository
        self._circuit_breaker = circuit_breaker or CircuitBreaker()

    async def execute(self, video: Video) -> IngestionRecord:
        """Execute video ingestion workflow."""
        record = await self._repository.get_by_video_id(video.video_id)
        if not record:
            record = IngestionRecord.create_pending(video)

        # Skip if already in final state
        if record.status in (IngestionStatus.COMPLETED, IngestionStatus.NO_TRANSCRIPT):
            logger.info("Video %s already processed (status: %s).", video.video_id, record.status)
            return record

        try:
            # Enforce 2-5s sequential rate limiting and verify circuit breaker state
            await self._circuit_breaker.throttle()

            logger.info("Fetching transcript for video: %s (%s)", video.title, video.video_id)
            paragraphs = await self._transcript_provider.get_transcript(video.video_id)

            vault_path = await self._vault_writer.write_note(
                video=video,
                transcript_paragraphs=paragraphs,
                status=IngestionStatus.COMPLETED,
            )
            record.mark_completed(vault_path=vault_path)
            await self._repository.update_record(record)
            logger.info("Successfully ingested note to: %s", vault_path)
            return record

        except TranscriptNotFoundError as exc:
            logger.warning("No transcript found for video %s: %s", video.video_id, exc)
            vault_path = await self._vault_writer.write_note(
                video=video,
                transcript_paragraphs=None,
                status=IngestionStatus.NO_TRANSCRIPT,
            )
            record.mark_no_transcript(vault_path=vault_path)
            await self._repository.update_record(record)
            return record

        except RateLimitExceededError as exc:
            logger.error("Rate limit exceeded while processing video %s: %s", video.video_id, exc)
            self._circuit_breaker.trip(cooldown_seconds=900)
            record.mark_failed(error_message=str(exc))
            await self._repository.update_record(record)
            return record

        except Exception as exc:
            logger.error("Unexpected error ingesting video %s: %s", video.video_id, exc)
            record.mark_failed(error_message=str(exc))
            await self._repository.update_record(record)
            return record
