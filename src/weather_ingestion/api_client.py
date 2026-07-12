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


def validate_response_payload(payload: dict[str, Any]) -> None:
    """
    Validate that the API response contains the expected hourly data.
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

    if "time" not in hourly_data or not hourly_data["time"]:
        raise ValueError("API response does not contain hourly timestamps.")


def fetch_weather_forecast(
    location: dict[str, Any],
    ingestion_config: dict[str, Any],
) -> dict[str, Any]:
    """
    Request and return the raw forecast payload for one location.

    Retries failed requests according to ingestion_config.yml.
    """
    base_url = ingestion_config["source"]["base_url"]
    execution_config = ingestion_config["execution"]

    timeout_seconds = execution_config["request_timeout_seconds"]
    max_retries = execution_config["max_retries"]
    retry_delay_seconds = execution_config["retry_delay_seconds"]

    params = build_request_params(location, ingestion_config)

    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(
                base_url,
                params=params,
                timeout=timeout_seconds,
            )

            response.raise_for_status()

            payload = response.json()
            validate_response_payload(payload)

            return payload

        except (
            requests.RequestException,
            ValueError,
        ) as error:
            last_error = error

            if attempt < max_retries:
                time.sleep(retry_delay_seconds)

    raise RuntimeError(
        f"Failed to retrieve weather data for "
        f"{location['location_id']} after {max_retries} attempts."
    ) from last_error


def fetch_all_active_locations() -> list[dict[str, Any]]:
    """
    Retrieve weather forecasts for every active configured location.
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
        payload = fetch_weather_forecast(
            location=location,
            ingestion_config=ingestion_config,
        )

        results.append(
            {
                "location_id": location["location_id"],
                "location_name": location["location_name"],
                "payload": payload,
            }
        )

    return results
