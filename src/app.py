"""Application library for python-circuitpython template.

This library provides temperature monitoring and MQTT publishing.
"""

import asyncio
import os
from typing import Final

from src.mqtt import MQTT_TOPIC, get_mqtt_client
from src.temperature.temperature_client import TemperatureClient

# System loop rate in seconds.
SYSTEM_RATE: Final[int] = 2

# Application mode - development runs one iteration, beta runs infinite loop.
MODE: Final[str] = os.getenv("MODE", "beta")


async def run() -> None:
    """
    Run the main application loop.

    Main application function that reads temperature and publishes to MQTT.
    Initializes clients and runs main application loop.
    Uses async context manager for automatic MQTT cleanup.

    Returns:
        None on successful initialization and first read (used for testing)
    """
    temp_client = TemperatureClient()

    async with await get_mqtt_client() as mqtt_client:
        while True:
            temp_f = temp_client.read_fahrenheit()

            # Publish temperature to MQTT
            await mqtt_client.publish(MQTT_TOPIC, payload=temp_f)

            if MODE == "development":
                return

            await asyncio.sleep(SYSTEM_RATE)
