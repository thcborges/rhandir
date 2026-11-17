"""PostgreSQL Connection Pool Manager using asyncpg."""

import asyncpg


async def create_db_pool(
    dsn: str,
    min_size: int = 1,
    max_size: int = 3,
) -> asyncpg.Pool:
    """Create a lightweight asyncpg connection pool with WAL optimization."""
    return await asyncpg.create_pool(
        dsn=dsn,
        min_size=min_size,
        max_size=max_size,
        command_timeout=60,
    )


async def close_db_pool(pool: asyncpg.Pool) -> None:
    """Gracefully close the asyncpg connection pool."""
    await pool.close()
