"""Circuit Breaker and Async Rate Limiting Service.

Enforces strict sequential rate limiting with random jitter (2-5 seconds)
and an automatic circuit breaker that pauses execution if HTTP 429/IP blocking is detected.
"""

import asyncio
import random
from datetime import UTC, datetime, timedelta

from rhandir.core.domain.exceptions import RateLimitExceededError


class CircuitBreaker:
    """Protects YouTube scrapers and APIs with jittered rate limiting and circuit breaking."""

    def __init__(
        self,
        min_delay_seconds: float = 2.0,
        max_delay_seconds: float = 5.0,
    ) -> None:
        self._min_delay = min_delay_seconds
        self._max_delay = max_delay_seconds
        self._tripped_until: datetime | None = None
        self._lock = asyncio.Lock()

    def is_tripped(self) -> bool:
        """Check if the circuit breaker is currently open/tripped."""
        if self._tripped_until is None:
            return False
        if datetime.now(UTC) >= self._tripped_until:
            self._tripped_until = None
            return False
        return True

    def trip(self, cooldown_seconds: int = 900) -> None:
        """Trip the circuit breaker, opening it for the specified cooldown."""
        self._tripped_until = datetime.now(UTC) + timedelta(seconds=cooldown_seconds)

    def ensure_operational(self) -> None:
        """Validate that the circuit is operational, otherwise raise RateLimitExceededError."""
        if self.is_tripped():
            remaining = int((self._tripped_until - datetime.now(UTC)).total_seconds())  # type: ignore[operator]
            msg = f"Circuit breaker tripped due to rate limiting. Cooling down for {remaining}s."
            raise RateLimitExceededError(msg)

    async def throttle(self) -> None:
        """Apply non-blocking async sleep with random jitter between min and max delays."""
        self.ensure_operational()
        async with self._lock:
            delay = random.uniform(self._min_delay, self._max_delay)
            await asyncio.sleep(delay)
