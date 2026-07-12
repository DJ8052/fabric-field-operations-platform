"""
api_client.py

Reusable client for requesting hourly weather forecasts from Open-Meteo.
"""

from __future__ import annotations

import time
from typing import Any

import requests

from weather_ingestion.config_loader import (
    load_ingestion_config,
    load_locations,
)


def build_request_params(
    location: dict[str, Any],
    ingestion_config: dict[str, Any],
) -> dict[str, Any]:
    """
    Build the Open-Meteo request parameters for one location.
    """
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
    """
    Validate that the response contains all required structures and variables.
    """
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

    if not timestamps:
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


def fetch_weather_forecast(
    location: dict[str, Any],
    ingestion_config: dict[str, Any],
) -> dict[str, Any]:
    """
    Retrieve one validated forecast payload.

    Returns the payload together with request-execution metadata.
    Raises RuntimeError after all configured attempts fail.
    """
    base_url = ingestion_config["source"]["base_url"]
    execution_config = ingestion_config["execution"]

    timeout_seconds = execution_config["request_timeout_seconds"]
    max_retries = execution_config["max_retries"]
    retry_delay_seconds = execution_config["retry_delay_seconds"]

    params = build_request_params(location, ingestion_config)

    last_error: Exception | None = None
    last_http_status: int | None = None

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(
                base_url,
                params=params,
                timeout=timeout_seconds,
            )

            last_http_status = response.status_code
            response.raise_for_status()

            payload = response.json()
            validate_response_payload(payload, ingestion_config)

            return {
                "payload": payload,
                "request_parameters": params,
                "attempt_count": attempt,
                "http_status_code": response.status_code,
            }

        except (
            requests.RequestException,
            ValueError,
        ) as error:
            last_error = error

            if attempt < max_retries:
                time.sleep(retry_delay_seconds)

    raise RuntimeError(
        f"Failed to retrieve weather data for "
        f"{location['location_id']} after {max_retries} attempts. "
        f"Last HTTP status: {last_http_status}. "
        f"Last error: {last_error}"
    ) from last_error


def fetch_all_active_locations() -> list[dict[str, Any]]:
    """
    Retrieve forecasts for every active configured location.

    Each location is isolated so one failure does not stop the batch.
    """
    locations_config = load_locations()
    ingestion_config = load_ingestion_config()

    results: list[dict[str, Any]] = []

    active_locations = [
        location
        for location in locations_config["locations"]
        if location.get("active", False)
    ]

    for location in active_locations:
        try:
            forecast_result = fetch_weather_forecast(
                location=location,
                ingestion_config=ingestion_config,
            )

            results.append(
                {
                    "location_id": location["location_id"],
                    "location_name": location["location_name"],
                    "status": "success",
                    "payload": forecast_result["payload"],
                    "request_parameters": forecast_result["request_parameters"],
                    "attempt_count": forecast_result["attempt_count"],
                    "http_status_code": forecast_result["http_status_code"],
                    "error_type": None,
                    "error_message": None,
                }
            )

        except Exception as error:
            results.append(
                {
                    "location_id": location["location_id"],
                    "location_name": location["location_name"],
                    "status": "failed",
                    "payload": None,
                    "request_parameters": None,
                    "attempt_count": ingestion_config["execution"]["max_retries"],
                    "http_status_code": None,
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                }
            )

    return results
