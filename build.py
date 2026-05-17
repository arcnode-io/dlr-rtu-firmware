"""
Build configuration for dlr-operating-envelope.

Loads configuration from cfg.yml based on ENV environment variable and
allows MQTT_PORT override from environment for dynamic test container ports.
Validates all config using Pydantic models.
"""

import enum
import os
from typing import Final

import yaml
from pydantic import BaseModel


class LogLevel(str, enum.Enum):
    """Logging levels for the application.

    Reason: `str, Enum` instead of `StrEnum` because this repo targets
    Python 3.10 (dnp3-python wheel constraint); StrEnum landed in 3.11.
    """

    ERROR = "ERROR"
    WARN = "WARN"
    INFO = "INFO"
    DEBUG = "DEBUG"


class Mode(str, enum.Enum):
    """Top-level deployment mode — picks sensor drivers + endpoint config.

    local: dev machine, all sensors sim, no DNP3 master expected.
    ci:    CI runner, all sensors sim, integration tests target localhost.
    demo:  Pi-deployed, DHT22 real (GPIO), other sensors sim until real
           drivers land. DNP3 outstation bound to LAN.
    """

    LOCAL = "local"
    CI = "ci"
    DEMO = "demo"


class Config(BaseModel):
    """Configuration for dlr-operating-envelope application."""

    log_level: LogLevel
    mqtt_host: str
    wifi_ssid: str
    mode: Mode = Mode.LOCAL
    # DNP3 outstation: where to listen + which DNP3 link-layer addresses to use.
    # Master is `ems-industrial-gateway` (configured separately on the gateway side).
    # Bind to all interfaces by default — the gateway connects across the LAN.
    dnp3_outstation_ip: str = "0.0.0.0"  # noqa: S104
    dnp3_outstation_port: int = 20000
    dnp3_master_addr: int = 2
    dnp3_outstation_addr: int = 1
    # POI line-to-line voltage (kV) used by DOE derivation to convert IEEE 738
    # ampacity into a watts-based envelope. 138 kV = typical sub-transmission
    # tie; override per-deployment when the real POI voltage differs.
    line_voltage_kv: float = 138.0


class _ConfigMap(BaseModel):
    """Configuration map for all environments."""

    local: Config
    ci: Config
    demo: Config


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
        case "demo":
            config = config_map.demo
        case _:
            config = config_map.local

    return config


# Load config at module import time
CONFIG: Final[Config] = load_config()

# MQTT port override for dynamic test container ports
MQTT_PORT: Final[int] = int(os.environ.get("MQTT_PORT", "1883"))
