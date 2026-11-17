"""Unit tests for CircuitBreaker and RateLimiter service.

BDD Specifications:
- Given a CircuitBreaker in normal state (CLOSED),
  When checking if it is tripped,
  Then it reports False.

- Given a CircuitBreaker,
  When trip() is called due to a rate limit or HTTP 429 block,
  Then is_tripped() reports True and calls fail fast with RateLimitExceededError.

- Given an expired cooldown period,
  When checking if it is tripped,
  Then it automatically recovers and reports False.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from rhandir.application.services.circuit_breaker import CircuitBreaker
from rhandir.core.domain.exceptions import RateLimitExceededError


def test_given_new_circuit_breaker_when_checking_tripped_then_returns_false() -> None:
    # Given
    cb = CircuitBreaker(min_delay_seconds=2.0, max_delay_seconds=5.0)

    # When / Then
    assert not cb.is_tripped()


def test_given_tripped_circuit_breaker_when_cooling_down_then_is_tripped_is_true() -> None:
    # Given
    cb = CircuitBreaker(min_delay_seconds=2.0, max_delay_seconds=5.0)

    # When
    cb.trip(cooldown_seconds=300)

    # Then
    assert cb.is_tripped()
    with pytest.raises(RateLimitExceededError):
        cb.ensure_operational()


def test_given_tripped_circuit_breaker_when_cooldown_elapses_then_recovers() -> None:
    # Given
    cb = CircuitBreaker(min_delay_seconds=2.0, max_delay_seconds=5.0)
    cb.trip(cooldown_seconds=60)

    # When simulating time passing beyond cooldown
    cb._tripped_until = datetime.now(UTC) - timedelta(seconds=1)

    # Then
    assert not cb.is_tripped()
    # ensure_operational should not raise
    cb.ensure_operational()


@pytest.mark.asyncio
async def test_given_rate_limiter_when_throttling_then_applies_jitter_delay() -> None:
    # Given
    cb = CircuitBreaker(min_delay_seconds=2.0, max_delay_seconds=5.0)

    # When
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await cb.throttle()

        # Then
        mock_sleep.assert_called_once()
        delay_arg = mock_sleep.call_args[0][0]
        assert 2.0 <= delay_arg <= 5.0
