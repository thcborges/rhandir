"""Core Message Listener Port."""

from typing import Protocol


class IMessageListener(Protocol):
    """Abstract port for asynchronous message listeners (e.g. Telegram Bot)."""

    async def start(self) -> None:
        """Start listening for incoming messages asynchronously."""
        ...

    async def stop(self) -> None:
        """Stop listening and release resources gracefully."""
        ...
