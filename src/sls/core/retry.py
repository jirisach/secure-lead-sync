from __future__ import annotations

import random
import time
from collections.abc import Callable
from typing import TypeVar

from sls.core.errors import RateLimitError, RetryableError
from sls.observability.logging import log_event

T = TypeVar("T")


def compute_backoff(attempt: int, base_delay: float = 1.0, max_delay: float = 8.0) -> float:
    """
    Exponential backoff with small jitter.
    attempt=1 -> about 1s
    attempt=2 -> about 2s
    attempt=3 -> about 4s
    capped by max_delay
    """
    raw = min(base_delay * (2 ** (attempt - 1)), max_delay)
    jitter = random.uniform(0, 0.25 * raw)
    return raw + jitter


def run_with_retry(
    operation: Callable[[], T],
    *,
    run_id: str,
    operation_name: str,
    max_attempts: int = 4,
    base_delay: float = 1.0,
    max_delay: float = 8.0,
) -> T:
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            result = operation()

            if attempt > 1:
                log_event(
                    "retry_succeeded",
                    run_id,
                    {
                        "operation_name": operation_name,
                        "attempt": attempt,
                    },
                )

            return result

        except RateLimitError as e:
            last_error = e

            if attempt >= max_attempts:
                log_event(
                    "retry_exhausted",
                    run_id,
                    {
                        "operation_name": operation_name,
                        "attempt": attempt,
                        "error_type": type(e).__name__,
                    },
                )
                raise

            delay = e.retry_after if e.retry_after is not None else compute_backoff(
                attempt, base_delay=base_delay, max_delay=max_delay
            )

            log_event(
                "rate_limited",
                run_id,
                {
                    "operation_name": operation_name,
                    "attempt": attempt,
                    "retry_in_seconds": round(delay, 2),
                    "error_type": type(e).__name__,
                },
            )
            time.sleep(delay)

        except RetryableError as e:
            last_error = e

            if attempt >= max_attempts:
                log_event(
                    "retry_exhausted",
                    run_id,
                    {
                        "operation_name": operation_name,
                        "attempt": attempt,
                        "error_type": type(e).__name__,
                    },
                )
                raise

            delay = compute_backoff(attempt, base_delay=base_delay, max_delay=max_delay)

            log_event(
                "retry_scheduled",
                run_id,
                {
                    "operation_name": operation_name,
                    "attempt": attempt,
                    "retry_in_seconds": round(delay, 2),
                    "error_type": type(e).__name__,
                },
            )
            time.sleep(delay)

    assert last_error is not None
    raise last_error