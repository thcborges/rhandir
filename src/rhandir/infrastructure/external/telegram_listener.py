"""Telegram Message Listener Adapter using aiogram."""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message

from rhandir.application.use_cases.ingest_video import IngestYouTubeVideoUseCase
from rhandir.core.domain.entities.video import Video
from rhandir.core.domain.value_objects.status import IngestionStatus
from rhandir.core.domain.value_objects.video_id import VideoId
from rhandir.core.ports.listeners import IMessageListener
from rhandir.core.ports.repositories import IIngestionRepository

logger = logging.getLogger(__name__)


def _format_quote(text: str) -> str:
    """Format original text as a clean markdown blockquote."""
    lines = text.strip().splitlines()
    return "\n".join(f"> {line}" for line in lines) if lines else "> (mensagem vazia)"


def _diagnose_error_cause(error_message: str | None) -> str:
    """Analyze error message and provide clear explanation of the root cause."""
    if not error_message:
        return "Causa desconhecida ou não especificada."
    err_lower = error_message.lower()
    if any(k in err_lower for k in ("429", "rate limit", "ipblocked", "requestblocked")):
        return (
            "Limite de requisições excedido ou bloqueio temporário de IP imposto pelo YouTube "
            "(HTTP 429 / Captcha). O Circuit Breaker foi ativado temporariamente para proteção."
        )
    if any(k in err_lower for k in ("permission denied", "vaultwriteerror", "no such file")):
        return (
            "Falha de permissão ou caminho inacessível ao tentar gravar a nota no Obsidian Vault."
        )
    if any(k in err_lower for k in ("database", "connection", "asyncpg", "postgres")):
        return "Falha de conexão ou persistência no banco de dados PostgreSQL."
    if any(k in err_lower for k in ("timeout", "timed out")):
        return "Tempo limite de comunicação esgotado durante a requisição de rede."
    return f"Falha operacional durante o processamento: {error_message}"


class TelegramListener(IMessageListener):
    """Listens for Telegram messages containing YouTube links and triggers ingestion."""

    def __init__(
        self,
        token: str,
        video_use_case: IngestYouTubeVideoUseCase,
        repository: IIngestionRepository,
        allowed_chat_ids: list[int] | None = None,
        bot: Bot | None = None,
        dp: Dispatcher | None = None,
    ) -> None:
        self._token = token
        self._video_use_case = video_use_case
        self._repository = repository
        self._allowed_chat_ids = set(allowed_chat_ids or [])
        self._bot = bot
        self._dp = dp
        self._polling_task: asyncio.Task[None] | None = None

    def _is_chat_authorized(self, chat_id: int) -> bool:
        """Verify whether a chat ID is authorized."""
        if not self._allowed_chat_ids:
            return True
        return chat_id in self._allowed_chat_ids

    async def handle_message(self, message: Message | Any) -> None:
        """Handle incoming Telegram messages and route YouTube links to ingestion."""
        chat_id = getattr(getattr(message, "chat", None), "id", None)
        if chat_id is not None and not self._is_chat_authorized(chat_id):
            logger.warning("Rejected unauthorized message from chat_id=%s", chat_id)
            await message.reply(f"⚠️ Chat ID {chat_id} não autorizado.")
            return

        raw_text = (
            getattr(message, "text", None) or getattr(message, "caption", None) or ""
        ).strip()

        if raw_text in ("/start", "/help"):
            quote = _format_quote(raw_text)
            welcome = (
                f"🤖 **Rhandir — Coletor Obsidian**\n\n"
                f"{quote}\n\n"
                "Envie um link de vídeo do YouTube (normal, shorts ou live) "
                "para que eu extraia e salve a transcrição na Pasta Máquina do Obsidian."
            )
            await message.reply(welcome)
            return

        video_id = VideoId.extract_from_text(raw_text)
        if not video_id:
            quote = _format_quote(raw_text)
            await message.reply(
                "📥 **Confirmação de Recebimento**\n\n"
                f"{quote}\n\n"
                "⚠️ Nenhum link válido de vídeo do YouTube foi encontrado na mensagem citada. "
                "Por favor, envie uma mensagem contendo uma URL do YouTube para processar."
            )
            return

        logger.info("Received YouTube video from Telegram: %s", video_id.value)
        video = Video(
            video_id=video_id,
            title=f"YouTube Video {video_id.value}",
            channel="Telegram Ingestion",
            url=video_id.to_url(),
            watched_at=None,
            discovered_at=datetime.now(UTC),
        )

        await self._repository.save_discovered(video)

        # 1. Immediate acknowledgment citing received message and link
        quote = _format_quote(raw_text)
        ack_message = (
            "📥 **Confirmação de Recebimento**\n\n"
            f"{quote}\n\n"
            f"🔗 **Link recebido:** {video.url}\n"
            "⏳ Iniciando extração e processamento da transcrição..."
        )
        await message.reply(ack_message)

        # 2. Process video and send detailed final status message
        try:
            record = await self._video_use_case.execute(video)

            if record.status == IngestionStatus.COMPLETED:
                final_reply = (
                    "📊 **Status do Processamento: Concluído com Sucesso** ✅\n\n"
                    f"• **ID do Vídeo:** `{video.video_id.value}`\n"
                    f"• **Link:** {video.url}\n"
                    f"• **Arquivo no Vault:** `{record.vault_path}`"
                )
                await message.reply(final_reply)

            elif record.status == IngestionStatus.NO_TRANSCRIPT:
                final_reply = (
                    "📊 **Status do Processamento: Sem Transcrição** ⚠️\n\n"
                    f"• **ID do Vídeo:** `{video.video_id.value}`\n"
                    f"• **Link:** {video.url}\n"
                    f"• **Nota criada no Vault:** `{record.vault_path}`\n"
                    "• **Detalhe:** Este vídeo não possui legendas disponíveis no YouTube. "
                    "Uma nota informativa de aviso foi salva no Vault para registro."
                )
                await message.reply(final_reply)

            else:
                cause = _diagnose_error_cause(record.error_message)
                final_reply = (
                    "📊 **Status do Processamento: Falha** ❌\n\n"
                    f"• **ID do Vídeo:** `{video.video_id.value}`\n"
                    f"• **Link:** {video.url}\n"
                    f"• **Erro:** `{record.error_message}`\n"
                    f"• **Causa do erro:** {cause}\n"
                    f"• **Tentativas:** {record.retry_count}"
                )
                await message.reply(final_reply)

        except Exception as exc:
            logger.error(
                "Unexpected error processing video %s: %s",
                video.video_id.value,
                exc,
                exc_info=True,
            )
            cause = _diagnose_error_cause(str(exc))
            final_reply = (
                "📊 **Status do Processamento: Falha Inesperada** ❌\n\n"
                f"• **ID do Vídeo:** `{video.video_id.value}`\n"
                f"• **Link:** {video.url}\n"
                f"• **Erro:** `{exc}`\n"
                f"• **Causa do erro:** {cause}"
            )
            await message.reply(final_reply)

    async def start(self) -> None:
        """Start the aiogram polling loop as a background task."""
        if not self._token:
            logger.warning("Telegram bot token not provided. Listener not started.")
            return

        if self._bot is None:
            self._bot = Bot(token=self._token)
        if self._dp is None:
            self._dp = Dispatcher()
            router = Router()
            router.message.register(self.handle_message)
            self._dp.include_router(router)

        logger.info("Starting Telegram Bot listener polling...")
        self._polling_task = asyncio.create_task(self._dp.start_polling(self._bot))

    async def stop(self) -> None:
        """Stop polling and close the bot session gracefully."""
        logger.info("Stopping Telegram Bot listener...")
        if self._dp is not None:
            await self._dp.stop_polling()
        if self._polling_task is not None and not self._polling_task.done():
            self._polling_task.cancel()
            try:
                await self._polling_task
            except (asyncio.CancelledError, Exception):
                pass
        if self._bot is not None and self._bot.session is not None:
            await self._bot.session.close()
        logger.info("Telegram Bot listener stopped.")
