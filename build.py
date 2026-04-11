"""
Build configuration for python-circuitpython.

Loads configuration from cfg.yml based on ENV environment variable and
allows MQTT_PORT override from environment for dynamic test container ports.
Validates all config using Pydantic models.
"""

import enum
import os
from typing import Final

import yaml
from pydantic import BaseModel


class LogLevel(enum.StrEnum):
    """Logging levels for the application."""

    ERROR = "ERROR"
    WARN = "WARN"
    INFO = "INFO"
    DEBUG = "DEBUG"


class Config(BaseModel):
    """Configuration for python-circuitpython application."""

    log_level: LogLevel
    mqtt_host: str
    wifi_ssid: str


class _ConfigMap(BaseModel):
    """Configuration map for all environments."""

    local: Config
    ci: Config


def load_config() -> Config:
    """
    Load configuration from cfg.yml file based on environment.

    Reads the configuration file and returns the appropriate config
    based on the ENV environment variable (defaults to 'local').
    Supports YAML merge keys (<<) for configuration inheritance.

    Returns:
        Config object for the current environment

    Raises:
        FileNotFoundError: If cfg.yml file is not found
        yaml.YAMLError: If cfg.yml contains invalid YAML
        KeyError: If environment not found in cfg.yml

    Example:
        >>> config = load_config()  # Uses ENV=local by default
        >>> config.log_level
        <LogLevel.DEBUG: 'DEBUG'>
    """
    # Determine environment (default to "local")
    environment = os.environ.get("ENV", "local")

    # Load and parse cfg.yml
    try:
        with open("cfg.yml") as file:
            # yaml.safe_load automatically handles merge keys (<<)
            yaml_content = yaml.safe_load(file)
            config_map = _ConfigMap(**yaml_content)
    except FileNotFoundError as e:
        raise FileNotFoundError("Failed to read cfg.yml") from e
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Failed to parse cfg.yml: {e}") from e

    # Select environment config
    match environment:
        case "ci":
            config = config_map.ci
        case _:
            config = config_map.local

    return config


# Load config at module import time
CONFIG: Final[Config] = load_config()

# MQTT port override for dynamic test container ports
MQTT_PORT: Final[int] = int(os.environ.get("MQTT_PORT", "1883"))
