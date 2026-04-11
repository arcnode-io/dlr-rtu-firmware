"""MQTT client for publishing sensor data."""

import logging
import os
from typing import Final

import aiomqtt

from build import CONFIG

# MQTT topic for publishing temperature readings
MQTT_TOPIC: Final[str] = "test/temp/F"


async def get_mqtt_client() -> aiomqtt.Client:
    """
    Create MQTT client configured for broker connection.

    Uses configuration from build.py for broker host and port.
    For integration tests, uses localhost when MQTT_PORT env var is set.

    Returns:
        Configured aiomqtt.Client instance (not yet connected)

    Example:
        >>> async with await get_mqtt_client() as client:
        ...     await client.publish("test/temp/F", payload=72.5)
    """
    # Read MQTT_PORT dynamically to support integration tests with dynamic ports
    mqtt_port = int(os.environ.get("MQTT_PORT", "1883"))
    # Reason: MQTT_HOST override needed when broker runs on a different machine (e.g. dev machine during HIL tests)
    mqtt_host = os.environ.get("MQTT_HOST", CONFIG.mqtt_host)

    logging.info(f"Connecting to MQTT broker at {mqtt_host}:{mqtt_port}")

    return aiomqtt.Client(
        hostname=mqtt_host, port=mqtt_port, identifier="circuitpython"
    )
