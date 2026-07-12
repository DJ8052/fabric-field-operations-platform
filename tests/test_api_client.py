from unittest.mock import Mock, patch

import pytest
import requests

from weather_ingestion.api_client import (
    fetch_all_active_locations,
    fetch_weather_forecast,
    validate_response_payload,
)


@pytest.fixture
def ingestion_config():
    return {
        "source": {
            "base_url": "https://api.open-meteo.com/v1/forecast",
        },
        "request": {
            "forecast_days": 7,
            "timeformat": "iso8601",
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "hourly_variables": [
                "temperature_2m",
                "relative_humidity_2m",
                "apparent_temperature",
                "precipitation",
                "weather_code",
                "wind_gusts_10m",
            ],
        },
        "execution": {
            "request_timeout_seconds": 30,
            "max_retries": 3,
            "retry_delay_seconds": 0,
        },
    }


@pytest.fixture
def location():
    return {
        "location_id": "TX-DAL",
        "location_name": "Dallas",
        "latitude": 32.7767,
        "longitude": -96.7970,
        "timezone": "America/Chicago",
        "active": True,
    }


@pytest.fixture
def valid_payload():
    hourly = {
        "time": ["2026-07-12T00:00", "2026-07-12T01:00"],
        "temperature_2m": [90.0, 89.0],
        "relative_humidity_2m": [45, 48],
        "apparent_temperature": [94.0, 93.0],
        "precipitation": [0.0, 0.0],
        "weather_code": [0, 0],
        "wind_gusts_10m": [12.0, 14.0],
    }

    return {
        "latitude": 32.7767,
        "longitude": -96.7970,
        "timezone": "America/Chicago",
        "hourly": hourly,
        "hourly_units": {},
    }


def test_validate_response_payload_accepts_valid_payload(
    valid_payload,
    ingestion_config,
):
    validate_response_payload(valid_payload, ingestion_config)


def test_validate_response_payload_rejects_missing_variable(
    valid_payload,
    ingestion_config,
):
    del valid_payload["hourly"]["wind_gusts_10m"]

    with pytest.raises(ValueError, match="missing requested hourly variables"):
        validate_response_payload(valid_payload, ingestion_config)


@patch("weather_ingestion.api_client.requests.get")
def test_fetch_weather_forecast_retries_non_200(
    mock_get,
    location,
    ingestion_config,
):
    failed_response = Mock()
    failed_response.status_code = 500
    failed_response.raise_for_status.side_effect = requests.HTTPError("500 error")

    mock_get.return_value = failed_response

    with pytest.raises(RuntimeError, match="after 3 attempts"):
        fetch_weather_forecast(location, ingestion_config)

    assert mock_get.call_count == 3


@patch("weather_ingestion.api_client.fetch_weather_forecast")
@patch("weather_ingestion.api_client.load_ingestion_config")
@patch("weather_ingestion.api_client.load_locations")
def test_fetch_all_active_locations_isolates_failures(
    mock_load_locations,
    mock_load_ingestion_config,
    mock_fetch_weather_forecast,
    ingestion_config,
    valid_payload,
):
    mock_load_locations.return_value = {
        "locations": [
            {
                "location_id": "TX-DAL",
                "location_name": "Dallas",
                "active": True,
            },
            {
                "location_id": "TX-HOU",
                "location_name": "Houston",
                "active": True,
            },
            {
                "location_id": "TX-AUS",
                "location_name": "Austin",
                "active": True,
            },
        ]
    }

    mock_load_ingestion_config.return_value = ingestion_config

    mock_fetch_weather_forecast.side_effect = [
        {
            "payload": valid_payload,
            "request_parameters": {},
            "attempt_count": 1,
            "http_status_code": 200,
        },
        RuntimeError("Houston failed after retries"),
        {
            "payload": valid_payload,
            "request_parameters": {},
            "attempt_count": 1,
            "http_status_code": 200,
        },
    ]

    results = fetch_all_active_locations()

    assert len(results) == 3
    assert results[0]["status"] == "success"
    assert results[1]["status"] == "failed"
    assert results[2]["status"] == "success"
