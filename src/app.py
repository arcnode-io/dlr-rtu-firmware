"""Application loop for dlr-rtu-firmware.

Each tick:
1. Read all five sensors (DHT, conductor temp, solar, rain, anemometer).
2. Compute IEEE 738 steady-state line ampacity from the readings.
3. Derive the import/export operating envelope from the ampacity.
4. Publish line rating + envelope + status via the DNP3 outstation.
5. Publish a heartbeat to MQTT.

The mode env (local | ci | demo) decides which driver each sensor uses.
"""

import asyncio
import logging
import os
from datetime import UTC, datetime
from typing import Final

import aiomqtt

from build import CONFIG
from src.dnp3_outstation import STATUS_OK, Dnp3Outstation
from src.doe import derive_envelope
from src.ieee738 import DRAKE_ACSR_795, steady_state_current
from src.mqtt import FloatSample, dynamic_line_rating_topic, get_mqtt_client, to_rfc3339
from src.sensor_suite import SensorSuite, build_sensor_suite

# Canonical topic per ADR-002; fixed for the process lifetime (site/device
# identity doesn't change at runtime).
LINE_RATING_TOPIC: Final[str] = dynamic_line_rating_topic(CONFIG)

# Tick rate seconds. DOE/line-rating physics is slow; 2s is plenty.
SYSTEM_RATE: Final[int] = 2

# "development" -> single tick (used by tests so the loop doesn't hang).
RUN_ONCE: Final[bool] = os.getenv("MODE") == "development"

_log = logging.getLogger(__name__)


def compute_tick(suite: SensorSuite) -> tuple[float, float]:
    """Read sensors, compute IEEE 738 ampacity + DOE limit.

    Returns:
        (line_rating_a, import_export_limit_w) -- symmetric envelope today.
    """
    dht = suite.dht.read()
    conductor_temp_c = suite.conductor_temp.read()
    solar_w_per_m2 = suite.solar.read()
    wind = suite.wind.read()
    # Rain isn't in IEEE 738; read for situational awareness only (future MQTT).
    _rain = suite.rain.read()

    # Wind=None (sensor void / cold / iced / offline) → fallback to natural
    # convection only by passing V_w = 0. IEEE 738's q_c term collapses to
    # the buoyancy-driven path → ampacity equals the conductor's static
    # rating. Same conservative direction as the icing-fallback policy.
    if wind is None:
        wind_speed_mps = 0.0
        wind_angle_deg = 90.0  # irrelevant at V_w = 0
    else:
        wind_speed_mps = wind.speed_mps
        wind_angle_deg = wind.direction_deg

    line_rating_a = steady_state_current(
        conductor=DRAKE_ACSR_795,
        conductor_temp_c=conductor_temp_c,
        ambient_temp_c=dht.temperature_c,
        wind_speed_mps=wind_speed_mps,
        solar_irradiance_w_per_m2=solar_w_per_m2,
        wind_angle_deg=wind_angle_deg,
    )
    envelope = derive_envelope(
        line_rating_a=line_rating_a,
        v_line_to_line_kv=CONFIG.line_voltage_kv,
    )
    return line_rating_a, envelope.import_limit_w


async def run() -> None:
    """Main loop: sensors -> IEEE 738 -> DOE -> outstation + MQTT."""
    suite = build_sensor_suite(CONFIG.mode)
    outstation = Dnp3Outstation(
        outstation_ip=CONFIG.dnp3_outstation_ip,
        port=CONFIG.dnp3_outstation_port,
        master_addr=CONFIG.dnp3_master_addr,
        outstation_addr=CONFIG.dnp3_outstation_addr,
    )
    await outstation.start()
    try:
        # Reason: a broken MQTT connection (broker restart, network blip)
        # otherwise crashes the whole process with an uncaught MqttError --
        # the outstation and sensor suite stay up, only the MQTT leg
        # reconnects. Matches the same fix on the dlr-pst-sim (ESP32) side.
        while True:
            try:
                async with await get_mqtt_client() as mqtt_client:
                    while True:
                        line_rating_a, limit_w = compute_tick(suite)

                        outstation.publish_line_rating(dynamic_amps=line_rating_a)
                        outstation.publish_envelope(
                            import_limit_w=limit_w,
                            export_limit_w=limit_w,
                        )
                        outstation.publish_status(
                            oe_status=STATUS_OK, lr_status=STATUS_OK
                        )

                        # QoS 0 / retain=true per ADR-002 §11 (measurements
                        # family): new subscribers see the latest value
                        # immediately, no delivery guarantee needed for
                        # high-rate telemetry.
                        sample = FloatSample(
                            ts=to_rfc3339(datetime.now(UTC)), value=line_rating_a
                        )
                        await mqtt_client.publish(
                            LINE_RATING_TOPIC,
                            payload=sample.model_dump_json(),
                            qos=0,
                            retain=True,
                        )
                        _log.debug(
                            "tick: line_rating=%.1fA limit=%.0fW",
                            line_rating_a,
                            limit_w,
                        )

                        if RUN_ONCE:
                            return
                        await asyncio.sleep(SYSTEM_RATE)
            except aiomqtt.MqttError:
                _log.warning("MQTT connection lost -- reconnecting in %ss", SYSTEM_RATE)
                await asyncio.sleep(SYSTEM_RATE)
    finally:
        await outstation.shutdown()
