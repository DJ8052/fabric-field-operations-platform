"""
Configuration settings for the Operational Data Generator.

This module contains all configurable values used throughout the
synthetic operational data generation process.

Changing values here changes the size and behavior of the generated
dataset without modifying the generator logic.
"""

from datetime import date

# ==========================================================
# Generation Calendar
# ==========================================================

GENERATION_YEAR = date.today().year

START_DATE = date(GENERATION_YEAR, 1, 1)
END_DATE = date(GENERATION_YEAR, 12, 31)

# ==========================================================
# Deterministic Generation
# ==========================================================

RANDOM_SEED = 20260101

# ==========================================================
# Target Entity Counts
# ==========================================================

NUM_REGIONS = 4
NUM_OFFICES = 12
NUM_EMPLOYEES = 150
NUM_PROJECTS = 75
NUM_JOB_SITES = 120
NUM_CREWS = 40
NUM_ACTIVITIES = 20
NUM_EQUIPMENT_TYPES = 10
NUM_EQUIPMENT = 80
NUM_EQUIPMENT_ASSIGNMENTS = 120
NUM_SAFETY_THRESHOLDS = 40
NUM_FIELD_SCHEDULES = 250

# ==========================================================
# Weather Locations (Version 1)
# ==========================================================

WEATHER_LOCATIONS = [
    "TX-DAL",
    "TX-HOU",
    "TX-AUS",
]

# ==========================================================
# Bronze Output Directory
# ==========================================================

BRONZE_OUTPUT_ROOT = "bronze/operations"

# ==========================================================
# Output Folder Names
# ==========================================================

ENTITY_FOLDERS = {
    "regions": "regions",
    "offices": "offices",
    "employees": "employees",
    "projects": "projects",
    "job_sites": "job_sites",
    "crews": "crews",
    "activities": "activities",
    "field_schedules": "field_schedules",
    "equipment_types": "equipment_types",
    "equipment": "equipment",
    "equipment_assignments": "equipment_assignments",
    "safety_thresholds": "safety_thresholds",
}