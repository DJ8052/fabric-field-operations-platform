"""Fixed configuration for deterministic operational source generation."""

from datetime import date

RANDOM_SEED = 20260101
START_DATE = date(2026, 1, 1)
END_DATE = date(2026, 12, 31)
INGESTION_DATE = date(2026, 1, 1)
RUN_ID = "accepted_20260101"

TARGET_COUNTS = {
    "regions": 4,
    "offices": 12,
    "employees": 150,
    "activities": 20,
    "equipment_types": 10,
    "safety_thresholds": 40,
    "projects": 75,
    "job_sites": 120,
    "crews": 40,
    "equipment": 80,
    "field_schedules": 250,
    "equipment_assignments": 120,
}

WEATHER_LOCATIONS = ("TX-DAL", "TX-HOU", "TX-AUS")

GENERATION_ORDER = tuple(TARGET_COUNTS)

ENTITY_FOLDERS = {name: name for name in TARGET_COUNTS}
