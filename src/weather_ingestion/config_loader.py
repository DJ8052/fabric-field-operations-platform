"""
config_loader.py

Utility functions for loading project configuration files.
"""

from pathlib import Path
import yaml

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]

CONFIG_DIR = PROJECT_ROOT / "config"


def load_locations():
    """
    Load locations.yml

    Returns:
        dict
    """
    file_path = CONFIG_DIR / "locations.yml"

    with open(file_path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def load_ingestion_config():
    """
    Load ingestion_config.yml

    Returns:
        dict
    """
    file_path = CONFIG_DIR / "ingestion_config.yml"

    with open(file_path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)
