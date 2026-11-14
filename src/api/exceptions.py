"""Custom domain exceptions for OpsCopilot API error boundaries."""

from typing import Optional


class OpsCopilotException(Exception):
    """Base exception for all domain errors within OpsCopilot."""

    def __init__(self, message: str, error_code: str = "INTERNAL_ERROR", status_code: int = 500) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code


class RateLimitException(OpsCopilotException):
    """Raised when upstream LLM (OpenAI) rate limits (HTTP 429) are encountered."""

    def __init__(
        self,
        message: str = "OpsCopilot rate limit exceeded. Please throttle requests and retry.",
        retry_after: int = 5,
    ) -> None:
        super().__init__(message=message, error_code="RATE_LIMIT_EXCEEDED", status_code=429)
        self.retry_after = retry_after


class UpstreamServiceException(OpsCopilotException):
    """Raised when upstream AI providers experience timeouts, DNS failures, or 503s."""

    def __init__(
        self,
        message: str = "Upstream AI service is temporarily unavailable or timed out.",
        retry_after: int = 10,
    ) -> None:
        super().__init__(message=message, error_code="UPSTREAM_SERVICE_UNAVAILABLE", status_code=503)
        self.retry_after = retry_after
