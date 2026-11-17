"""CLI Entrypoint for Rhandir daemon and manual synchronization."""

import asyncio
import logging
from typing import NamedTuple

import typer

from rhandir.application.services.circuit_breaker import CircuitBreaker
from rhandir.application.use_cases.ingest_history import IngestYouTubeHistoryUseCase
from rhandir.application.use_cases.ingest_video import IngestYouTubeVideoUseCase
from rhandir.infrastructure.config.settings import Settings
from rhandir.infrastructure.db.client import close_db_pool, create_db_pool
from rhandir.infrastructure.db.postgres_repository import PostgresIngestionRepository
from rhandir.infrastructure.external.takeout_parser import TakeoutCollector
from rhandir.infrastructure.external.youtube_transcript import YouTubeTranscriptProvider
from rhandir.infrastructure.filesystem.vault_writer import VaultWriter
from rhandir.interfaces.controllers.daemon import DaemonController

cli = typer.Typer(
    name="rhandir",
    help="Rhandir — Ingestão Leve para Segundo Cérebro Obsidian",
    no_args_is_help=True,
)

sync_app = typer.Typer(
    name="sync",
    help="Comandos de sincronização manual sob demanda",
    no_args_is_help=True,
)
cli.add_typer(sync_app, name="sync")


class AppContainer(NamedTuple):
    """Dependency container for use cases and controllers."""

    repository: PostgresIngestionRepository
    history_use_case: IngestYouTubeHistoryUseCase
    daemon_controller: DaemonController


def build_container(settings: Settings, pool: object) -> AppContainer:
    """Wire up clean architecture layers and dependencies (Composition Root)."""
    repository = PostgresIngestionRepository(pool=pool)  # type: ignore[arg-type]
    collector = TakeoutCollector(inbox_dir=settings.takeout_inbox_dir)
    transcript_provider = YouTubeTranscriptProvider()
    vault_writer = VaultWriter(output_dir=settings.obsidian_raw_dir)

    circuit_breaker = CircuitBreaker(
        min_delay_seconds=settings.transcript_rate_limit_delay_min,
        max_delay_seconds=settings.transcript_rate_limit_delay_max,
    )

    video_use_case = IngestYouTubeVideoUseCase(
        transcript_provider=transcript_provider,
        vault_writer=vault_writer,
        repository=repository,
        circuit_breaker=circuit_breaker,
    )

    history_use_case = IngestYouTubeHistoryUseCase(
        collector=collector,
        repository=repository,
        video_use_case=video_use_case,
        circuit_breaker=circuit_breaker,
    )

    daemon_controller = DaemonController(
        history_use_case=history_use_case,
        poll_interval_seconds=settings.daemon_poll_interval_seconds,
    )

    return AppContainer(
        repository=repository,
        history_use_case=history_use_case,
        daemon_controller=daemon_controller,
    )


@cli.command("status")
def status_command() -> None:
    """Exibe a contagem de vídeos por status, saúde do banco e métricas de ingestão."""
    settings = Settings()

    async def _run() -> None:
        typer.echo("Conectando ao PostgreSQL...")
        try:
            pool = await create_db_pool(settings.database_url)
        except Exception as exc:
            typer.secho(f"Erro ao conectar ao banco de dados: {exc}", fg=typer.colors.RED)
            raise typer.Exit(code=1) from exc

        try:
            repo = PostgresIngestionRepository(pool)
            await repo.init_schema()
            counts = await repo.get_status_counts()

            typer.secho("\n--- Status do Rhandir (PostgreSQL WAL) ---", fg=typer.colors.CYAN)
            if not counts:
                typer.echo("Nenhum vídeo registrado até o momento.")
            else:
                for status, count in sorted(counts.items()):
                    typer.echo(f"  • {status:15}: {count}")
            typer.secho("------------------------------------------\n", fg=typer.colors.CYAN)
        finally:
            await close_db_pool(pool)

    asyncio.run(_run())


@sync_app.command("youtube")
def sync_youtube_command(
    max_items: int = typer.Option(100, "--max-items", "-m", help="Limite de vídeos por execução"),
) -> None:
    """Executa um ciclo único de ingestão do histórico do YouTube."""
    settings = Settings()

    async def _run() -> None:
        typer.echo(f"Iniciando sincronização do YouTube (inbox: {settings.takeout_inbox_dir})...")
        try:
            pool = await create_db_pool(settings.database_url)
        except Exception as exc:
            typer.secho(f"Erro ao conectar ao PostgreSQL: {exc}", fg=typer.colors.RED)
            raise typer.Exit(code=1) from exc

        try:
            container = build_container(settings, pool)
            await container.repository.init_schema()
            summary = await container.history_use_case.execute(max_items=max_items)

            typer.secho("\nSincronização concluída com sucesso!", fg=typer.colors.GREEN)
            typer.echo(
                f"Resultado: total_discovered={summary.total_discovered}, "
                f"newly_discovered={summary.newly_discovered}, "
                f"completed={summary.completed}, "
                f"no_transcript={summary.no_transcript}, "
                f"failed={summary.failed}, "
                f"skipped_duplicates={summary.skipped_duplicates}"
            )
        finally:
            await close_db_pool(pool)

    asyncio.run(_run())


@cli.command("run")
def run_command() -> None:
    """Inicia o daemon do Rhandir em primeiro plano."""
    settings = Settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    async def _run() -> None:
        typer.echo("Iniciando o serviço Rhandir em background...")
        try:
            pool = await create_db_pool(settings.database_url)
        except Exception as exc:
            typer.secho(f"Falha ao conectar no PostgreSQL: {exc}", fg=typer.colors.RED)
            raise typer.Exit(code=1) from exc

        try:
            container = build_container(settings, pool)
            await container.repository.init_schema()
            await container.daemon_controller.run()
        finally:
            await close_db_pool(pool)

    try:
        asyncio.run(_run())
    except (KeyboardInterrupt, SystemExit):
        typer.echo("Execução interrompida pelo usuário.")


def main() -> None:
    """Entry point for project console script."""
    cli()


if __name__ == "__main__":
    main()
