"""Application library for dlr-operating-envelope.

This library provides temperature monitoring, MQTT publishing, and a DNP3
outstation that ems-industrial-gateway polls for DOE + line-rating values.
"""

import asyncio
import os
from typing import Final

from build import CONFIG
from src.dnp3_outstation import Dnp3Outstation
from src.mqtt import MQTT_TOPIC, get_mqtt_client
from src.temperature.temperature_client import TemperatureClient

# System loop rate in seconds.
SYSTEM_RATE: Final[int] = 2

# Application mode - development runs one iteration, beta runs infinite loop.
MODE: Final[str] = os.getenv("MODE", "beta")


async def run() -> None:
    """
    Run the main application loop.

    Main application function that reads temperature, publishes to MQTT, and
    serves the DNP3 outstation. Initializes clients, starts the outstation,
    runs the read/publish loop, and shuts down the outstation cleanly on exit.

    Returns:
        None on successful initialization and first read (used for testing)
    """
    temp_client = TemperatureClient()
    outstation = Dnp3Outstation(
        outstation_ip=CONFIG.dnp3_outstation_ip,
        port=CONFIG.dnp3_outstation_port,
        master_addr=CONFIG.dnp3_master_addr,
        outstation_addr=CONFIG.dnp3_outstation_addr,
    )
    outstation.start()
    try:
        async with await get_mqtt_client() as mqtt_client:
            while True:
                temp_f = temp_client.read_fahrenheit()

                # Publish temperature to MQTT
                await mqtt_client.publish(MQTT_TOPIC, payload=temp_f)

                # Heartbeat the outstation status as healthy — IEEE 738 +
                # DOE-derivation code (separate task) overwrites with real
                # values via outstation.publish_envelope / publish_line_rating.
                outstation.publish_status(oe_status=0, lr_status=0)

                if MODE == "development":
                    return

                await asyncio.sleep(SYSTEM_RATE)
    finally:
        outstation.shutdown()
