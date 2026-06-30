class OpenEvalsError(Exception):
    """Base exception for OpenEvals."""


class MetricInputError(OpenEvalsError):
    """Raised when a metric receives invalid input."""


class JudgeModelError(OpenEvalsError):
    """Raised when a judge model call fails."""


class PipelineError(OpenEvalsError):
    """Raised when the evaluation pipeline encounters an error."""


class DatabaseError(OpenEvalsError):
    """Raised when a database operation fails."""


class AuthenticationError(OpenEvalsError):
    """Raised when authentication fails."""


class RateLimitError(OpenEvalsError):
    """Raised when rate limit is exceeded."""


class DatasetError(OpenEvalsError):
    """Raised when dataset loading fails."""


class CircuitBreakerOpenError(JudgeModelError):
    """Raised when circuit breaker is open for a judge model."""
