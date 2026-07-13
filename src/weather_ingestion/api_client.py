"""
Reusable client for requesting hourly weather forecasts from Open-Meteo.
"""

from __future__ import annotations

import random
import time
from typing import Any

import requests

from weather_ingestion.config_loader import (
    load_ingestion_config,
    load_locations,
)
from weather_ingestion.exceptions import WeatherIngestionError


RETRYABLE_HTTP_STATUS_CODES = {429, 500, 502, 503, 504}


def build_request_params(
    location: dict[str, Any],
    ingestion_config: dict[str, Any],
) -> dict[str, Any]:
    """Build the Open-Meteo request parameters for one location."""
    request_config = ingestion_config["request"]

    return {
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "hourly": ",".join(request_config["hourly_variables"]),
        "temperature_unit": request_config["temperature_unit"],
        "wind_speed_unit": request_config["wind_speed_unit"],
        "precipitation_unit": request_config["precipitation_unit"],
        "timeformat": request_config["timeformat"],
        "timezone": location["timezone"],
        "forecast_days": request_config["forecast_days"],
    }


def validate_response_payload(
    payload: dict[str, Any],
    ingestion_config: dict[str, Any],
) -> None:
    """Validate that the response contains all required structures and variables."""
    if not isinstance(payload, dict):
        raise ValueError("API response payload must be a JSON object.")

    required_top_level_fields = {
        "latitude",
        "longitude",
        "timezone",
        "hourly",
        "hourly_units",
    }

    missing_fields = required_top_level_fields - payload.keys()

    if missing_fields:
        raise ValueError(
            f"API response is missing required fields: {sorted(missing_fields)}"
        )

    hourly_data = payload["hourly"]

    if not isinstance(hourly_data, dict):
        raise ValueError("API response field 'hourly' is not an object.")

    timestamps = hourly_data.get("time")

    if not isinstance(timestamps, list) or not timestamps:
        raise ValueError("API response does not contain hourly timestamps.")

    requested_variables = ingestion_config["request"]["hourly_variables"]

    missing_variables = [
        variable
        for variable in requested_variables
        if variable not in hourly_data
    ]

    if missing_variables:
        raise ValueError(
            "API response is missing requested hourly variables: "
            f"{missing_variables}"
        )

    expected_length = len(timestamps)

    inconsistent_variables = [
        variable
        for variable in requested_variables
        if not isinstance(hourly_data[variable], list)
        or len(hourly_data[variable]) != expected_length
    ]

    if inconsistent_variables:
        raise ValueError(
            "Hourly variables do not align with the timestamp count: "
            f"{inconsistent_variables}"
        )


def _calculate_backoff_seconds(
    base_delay_seconds: float,
    attempt: int,
) -> float:
    """Calculate exponential backoff with small jitter."""
    exponential_delay = base_delay_seconds * (2 ** (attempt - 1))
    jitter = random.uniform(0, max(base_delay_seconds * 0.1, 0.001))
    return exponential_delay + jitter


def fetch_weather_forecast(
    location: dict[str, Any],
    ingestion_config: dict[str, Any],
    session: requests.Session | None = None,
) -> dict[str, Any]:
    """
    Retrieve one validated forecast payload.

    Retries only transient network failures and retryable HTTP status codes.
    Validation failures and non-retryable HTTP errors fail immediately.
    """
    base_url = ingestion_config["source"]["base_url"]
    execution_config = ingestion_config["execution"]

    timeout_seconds = execution_config["request_timeout_seconds"]
    max_retries = execution_config["max_retries"]
    retry_delay_seconds = execution_config["retry_delay_seconds"]

    params = build_request_params(location, ingestion_config)
    http_client = session or requests.Session()

    last_error: Exception | None = None
    last_http_status: int | None = None

    for attempt in range(1, max_retries + 1):
        try:
            response = http_client.get(
                base_url,
                params=params,
                timeout=timeout_seconds,
            )

            last_http_status = response.status_code

            if response.status_code in RETRYABLE_HTTP_STATUS_CODES:
                raise WeatherIngestionError(
                    (
                        f"Retryable HTTP status "
                        f"{response.status_code} for "
                        f"{location['location_id']}."
                    ),
                    location_id=location["location_id"],
                    attempt_count=attempt,
                    http_status_code=response.status_code,
                    error_category="retryable_http",
                )

            if 400 <= response.status_code < 500:
                raise WeatherIngestionError(
                    (
                        f"Non-retryable HTTP status "
                        f"{response.status_code} for "
                        f"{location['location_id']}."
                    ),
                    location_id=location["location_id"],
                    attempt_count=attempt,
                    http_status_code=response.status_code,
                    error_category="non_retryable_http",
                )

            response.raise_for_status()

            try:
                payload = response.json()
            except ValueError as error:
                raise WeatherIngestionError(
                    (
                        f"Invalid JSON response for "
                        f"{location['location_id']}."
                    ),
                    location_id=location["location_id"],
                    attempt_count=attempt,
                    http_status_code=response.status_code,
                    error_category="invalid_json",
                ) from error

            try:
                validate_response_payload(payload, ingestion_config)
            except ValueError as error:
                raise WeatherIngestionError(
                    str(error),
                    location_id=location["location_id"],
                    attempt_count=attempt,
                    http_status_code=response.status_code,
                    error_category="payload_validation",
                ) from error

            return {
                "payload": payload,
                "request_parameters": params,
                "attempt_count": attempt,
                "http_status_code": response.status_code,
            }

        except WeatherIngestionError as error:
            last_error = error
            last_http_status = error.http_status_code

            if error.error_category not in {"retryable_http"}:
                raise

        except (
            requests.Timeout,
            requests.ConnectionError,
        ) as error:
            last_error = error

        except requests.RequestException as error:
            raise WeatherIngestionError(
                (
                    f"Non-retryable request failure for "
                    f"{location['location_id']}: {error}"
                ),
                location_id=location["location_id"],
                attempt_count=attempt,
                http_status_code=last_http_status,
                error_category="request_error",
            ) from error

        if attempt < max_retries:
            time.sleep(
                _calculate_backoff_seconds(
                    retry_delay_seconds,
                    attempt,
                )
            )

    error_category = (
        last_error.error_category
        if isinstance(last_error, WeatherIngestionError)
        else "network_error"
    )

    raise WeatherIngestionError(
        (
            f"Failed to retrieve weather data for "
            f"{location['location_id']} after "
            f"{max_retries} attempts."
        ),
        location_id=location["location_id"],
        attempt_count=max_retries,
        http_status_code=last_http_status,
        error_category=error_category,
    ) from last_error


def fetch_all_active_locations() -> list[dict[str, Any]]:
    """
    Retrieve forecasts for every active configured location.

    Each known ingestion failure is isolated so one location does not stop
    the batch. Unexpected programming errors are allowed to surface.
    """
    locations_config = load_locations()
    ingestion_config = load_ingestion_config()

    results: list[dict[str, Any]] = []

    active_locations = [
        location
        for location in locations_config["locations"]
        if location["active"]
    ]

    with requests.Session() as session:
        for location in active_locations:
            try:
                forecast_result = fetch_weather_forecast(
                    location=location,
                    ingestion_config=ingestion_config,
                    session=session,
                )

                results.append(
                    {
                        "location_id": location["location_id"],
                        "location_name": location["location_name"],
                        "status": "success",
                        "payload": forecast_result["payload"],
                        "request_parameters": forecast_result[
                            "request_parameters"
                        ],
                        "attempt_count": forecast_result["attempt_count"],
                        "http_status_code": forecast_result[
                            "http_status_code"
                        ],
                        "error_category": None,
                        "error_type": None,
                        "error_message": None,
                    }
                )

            except WeatherIngestionError as error:
                results.append(
                    {
                        "location_id": location["location_id"],
                        "location_name": location["location_name"],
                        "status": "failed",
                        "payload": None,
                        "request_parameters": build_request_params(
                            location,
                            ingestion_config,
                        ),
                        "attempt_count": error.attempt_count,
                        "http_status_code": error.http_status_code,
                        "error_category": error.error_category,
                        "error_type": type(error).__name__,
                        "error_message": str(error),
                    }
                )

    return results
