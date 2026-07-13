"""
Custom exceptions used by the weather ingestion package.
"""

from __future__ import annotations


class ConfigurationError(ValueError):
    """Raised when a project configuration file is missing or invalid."""


class WeatherIngestionError(RuntimeError):
    """
    Raised when a weather API request fails.

    Attributes:
        location_id: Location associated with the failed request.
        attempt_count: Number of request attempts made.
        http_status_code: Last HTTP status received, when available.
        error_category: Normalized operational failure category.
    """

    def __init__(
        self,
        message: str,
        *,
        location_id: str,
        attempt_count: int,
        http_status_code: int | None = None,
        error_category: str = "unknown",
    ) -> None:
        super().__init__(message)
        self.location_id = location_id
        self.attempt_count = attempt_count
        self.http_status_code = http_status_code
        self.error_category = error_category
