"""
Utility functions for loading and validating project configuration files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml

from weather_ingestion.exceptions import ConfigurationError


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"


def _load_yaml(file_path: Path) -> dict[str, Any]:
    """Load a YAML file and ensure that it contains a mapping."""
    if not file_path.exists():
        raise ConfigurationError(
            f"Configuration file does not exist: {file_path}"
        )

    try:
        with file_path.open("r", encoding="utf-8") as file:
            content = yaml.safe_load(file)
    except yaml.YAMLError as error:
        raise ConfigurationError(
            f"Invalid YAML syntax in {file_path.name}: {error}"
        ) from error

    if content is None:
        raise ConfigurationError(
            f"Configuration file is empty: {file_path.name}"
        )

    if not isinstance(content, dict):
        raise ConfigurationError(
            f"Configuration file must contain a YAML mapping: "
            f"{file_path.name}"
        )

    return content


def _require_fields(
    config: dict[str, Any],
    required_fields: set[str],
    context: str,
) -> None:
    """Raise an error when required configuration fields are missing."""
    missing_fields = required_fields - config.keys()

    if missing_fields:
        raise ConfigurationError(
            f"{context} is missing required fields: "
            f"{sorted(missing_fields)}"
        )


def _validate_location(location: dict[str, Any], index: int) -> None:
    """Validate one configured location."""
    context = f"locations[{index}]"

    required_fields = {
        "location_id",
        "location_name",
        "latitude",
        "longitude",
        "timezone",
        "active",
    }

    _require_fields(location, required_fields, context)

    if not isinstance(location["location_id"], str) or not location[
        "location_id"
    ].strip():
        raise ConfigurationError(
            f"{context}.location_id must be a non-empty string."
        )

    if not isinstance(location["location_name"], str) or not location[
        "location_name"
    ].strip():
        raise ConfigurationError(
            f"{context}.location_name must be a non-empty string."
        )

    latitude = location["latitude"]
    longitude = location["longitude"]

    if (
        not isinstance(latitude, (int, float))
        or isinstance(latitude, bool)
        or not -90 <= latitude <= 90
    ):
        raise ConfigurationError(
            f"{context}.latitude must be between -90 and 90."
        )

    if (
        not isinstance(longitude, (int, float))
        or isinstance(longitude, bool)
        or not -180 <= longitude <= 180
    ):
        raise ConfigurationError(
            f"{context}.longitude must be between -180 and 180."
        )

    timezone = location["timezone"]

    if not isinstance(timezone, str) or not timezone.strip():
        raise ConfigurationError(
            f"{context}.timezone must be a non-empty string."
        )

    try:
        ZoneInfo(timezone)
    except ZoneInfoNotFoundError as error:
        raise ConfigurationError(
            f"{context}.timezone is not valid: {timezone}"
        ) from error

    if not isinstance(location["active"], bool):
        raise ConfigurationError(
            f"{context}.active must be true or false."
        )


def validate_locations_config(config: dict[str, Any]) -> None:
    """Validate the complete locations configuration."""
    _require_fields(config, {"locations"}, "locations configuration")

    locations = config["locations"]

    if not isinstance(locations, list) or not locations:
        raise ConfigurationError(
            "locations must be a non-empty list."
        )

    seen_location_ids: set[str] = set()

    for index, location in enumerate(locations):
        if not isinstance(location, dict):
            raise ConfigurationError(
                f"locations[{index}] must be a YAML mapping."
            )

        _validate_location(location, index)

        location_id = location["location_id"]

        if location_id in seen_location_ids:
            raise ConfigurationError(
                f"Duplicate location_id found: {location_id}"
            )

        seen_location_ids.add(location_id)


def validate_ingestion_config(config: dict[str, Any]) -> None:
    """Validate the complete ingestion configuration."""
    _require_fields(
        config,
        {"source", "request", "execution", "bronze"},
        "ingestion configuration",
    )

    source = config["source"]
    request = config["request"]
    execution = config["execution"]
    bronze = config["bronze"]

    for section_name, section in {
        "source": source,
        "request": request,
        "execution": execution,
        "bronze": bronze,
    }.items():
        if not isinstance(section, dict):
            raise ConfigurationError(
                f"{section_name} must be a YAML mapping."
            )

    _require_fields(
        source,
        {"source_system", "endpoint_name", "base_url"},
        "source",
    )

    if not isinstance(source["base_url"], str) or not source[
        "base_url"
    ].startswith(("http://", "https://")):
        raise ConfigurationError(
            "source.base_url must be a valid HTTP or HTTPS URL."
        )

    _require_fields(
        request,
        {
            "forecast_days",
            "timeformat",
            "temperature_unit",
            "wind_speed_unit",
            "precipitation_unit",
            "hourly_variables",
        },
        "request",
    )

    if (
        not isinstance(request["forecast_days"], int)
        or isinstance(request["forecast_days"], bool)
        or request["forecast_days"] <= 0
    ):
        raise ConfigurationError(
            "request.forecast_days must be a positive integer."
        )

    hourly_variables = request["hourly_variables"]

    if not isinstance(hourly_variables, list) or not hourly_variables:
        raise ConfigurationError(
            "request.hourly_variables must be a non-empty list."
        )

    if not all(
        isinstance(variable, str) and variable.strip()
        for variable in hourly_variables
    ):
        raise ConfigurationError(
            "Every hourly variable must be a non-empty string."
        )

    if len(hourly_variables) != len(set(hourly_variables)):
        raise ConfigurationError(
            "request.hourly_variables contains duplicate values."
        )

    _require_fields(
        execution,
        {
            "request_timeout_seconds",
            "max_retries",
            "retry_delay_seconds",
        },
        "execution",
    )

    timeout_seconds = execution["request_timeout_seconds"]
    max_retries = execution["max_retries"]
    retry_delay_seconds = execution["retry_delay_seconds"]

    if (
        not isinstance(timeout_seconds, (int, float))
        or isinstance(timeout_seconds, bool)
        or timeout_seconds <= 0
    ):
        raise ConfigurationError(
            "execution.request_timeout_seconds must be greater than zero."
        )

    if (
        not isinstance(max_retries, int)
        or isinstance(max_retries, bool)
        or max_retries <= 0
    ):
        raise ConfigurationError(
            "execution.max_retries must be a positive integer."
        )

    if (
        not isinstance(retry_delay_seconds, (int, float))
        or isinstance(retry_delay_seconds, bool)
        or retry_delay_seconds < 0
    ):
        raise ConfigurationError(
            "execution.retry_delay_seconds cannot be negative."
        )

    _require_fields(
        bronze,
        {"lakehouse_name", "root_path", "path_pattern"},
        "bronze",
    )

    for field_name in {
        "lakehouse_name",
        "root_path",
        "path_pattern",
    }:
        if not isinstance(bronze[field_name], str) or not bronze[
            field_name
        ].strip():
            raise ConfigurationError(
                f"bronze.{field_name} must be a non-empty string."
            )


def load_locations() -> dict[str, Any]:
    """Load and validate locations.yml."""
    config = _load_yaml(CONFIG_DIR / "locations.yml")
    validate_locations_config(config)
    return config


def load_ingestion_config() -> dict[str, Any]:
    """Load and validate ingestion_config.yml."""
    config = _load_yaml(CONFIG_DIR / "ingestion_config.yml")
    validate_ingestion_config(config)
    return config
