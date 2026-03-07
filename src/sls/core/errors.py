from __future__ import annotations


class SlsError(Exception):
    """Base application error."""


class RetryableError(SlsError):
    """Temporary error, safe to retry."""


class NonRetryableError(SlsError):
    """Permanent error, do not retry."""


class RateLimitError(RetryableError):
    """Rate limited by upstream API."""

    def __init__(self, message: str = "Rate limited", retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class ApiTimeoutError(RetryableError):
    """Request timed out."""


class ApiServerError(RetryableError):
    """5xx upstream server error."""


class ApiBadRequestError(NonRetryableError):
    """400-level request/data error."""


class ApiUnauthorizedError(NonRetryableError):
    """401/403 auth error."""