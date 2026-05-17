# DLR Operating Envelope 🌡️📈

![](https://img.shields.io/gitlab/pipeline-status/arcnode-io/dlr-operating-envelope?branch=main&logo=gitlab)
![](https://gitlab.com/arcnode-io/dlr-operating-envelope/badges/main/coverage.svg)
![](https://img.shields.io/badge/ty_checked-gray?logo=astral)
![](https://img.shields.io/badge/3.13-gray?logo=python)
![](https://img.shields.io/badge/uv-gray?logo=uv)
![](https://img.shields.io/badge/mqtt-gray?logo=mqtt)
![](https://img.shields.io/badge/pi_compatible-gray?logo=raspberrypi)

> Environmental sensor collection and IEEE 738 dynamic line rating calculations

## Pre-requisites
- python 3.13+
- Raspberry Pi

## Sensors

| Sensor | Interface | Purpose | Data Type |
|--------|-----------|---------|-----------|
| FLIR Lepton | SPI | Conductor temperature | Thermal imaging |
| DHT22 | GPIO | Ambient temp/humidity | Digital |
| SI1145 | I2C | Solar radiation | UV/Visible/IR |
| YL-83 | ADC | Rain detection | Analog |
| Calypso ULP STD ultrasonic | I2C | Wind speed + direction | Digital |

Anemometer required for IEEE 738 compliance — convective cooling from wind is the dominant heat-dissipation mechanism for overhead conductors. Ultrasonic preferred over cup-style: zero stall speed, no inertia, accurate at the low wind speeds where DLR matters most.

**Component choice:** Calypso Instruments **ULP STD Ultrasonic Wind Meter** — 0.12 W average draw fits the solar/LiFePO4 budget, runs over the **existing I2C bus** (no new transceiver IC needed on the carrier — same bus as the SI1145), gives speed + direction in one telegram. Marine-origin IP-rated enclosure for outdoor mast mount.

**Cheaper fallback:** Modern Devices Wind Sensor Rev. P (MEMS hot-wire, analog 0–3.3V) — reuses an ADS1115 channel; no direction.

## Core Algorithm

Dynamic rating calculation using IEEE 738 standard:

$$ P_{max} = \frac{(T_{max} - T_{amb} - ΔT_{solar} + ΔT_{rain})}{R_{thermal}} $$

Where:
- Conductor max temp (80°C): $T_{max}$
- DHT22 reading: $T_{amb}$
- SI1145 radiation factor: $ΔT_{solar}$
- YL-83 cooling coefficient: $ΔT_{rain}$
- FLIR Lepton thermal resistance: $R_{thermal} = \frac{(T_{conductor} - T_{ambient})}{P_{current}}$

## Context Deployment

```plantuml
rectangle dlr_operating_envelope

cloud sensors
queue mqtt_broker
rectangle dlr_pst_sim
rectangle industrial_gateway

dlr_operating_envelope -- sensors
dlr_operating_envelope -- mqtt_broker: mqtt
mqtt_broker -- dlr_pst_sim
dlr_operating_envelope -- industrial_gateway: dnp3
```

## Context Sequence

```plantuml
participant sensors
participant dlr_operating_envelope
participant dlr_pst_sim
participant industrial_gateway

sensors -> dlr_operating_envelope: environmental readings
dlr_operating_envelope -> dlr_pst_sim: mqtt measurements
industrial_gateway -> dlr_operating_envelope: poll dnp3 points
```

## Deployment

```plantuml
rectangle dlr_operating_envelope #line.dashed {
  rectangle thermal_camera
  rectangle temp_humidity_sensor
  rectangle uv_light_sensor
  rectangle rain_sensor
  rectangle ieee738_calc
  rectangle mqtt_publisher
  rectangle dnp3_outstation
}

queue mqtt_broker
rectangle industrial_gateway

dlr_operating_envelope -- mqtt_broker: mqtt
dlr_operating_envelope -- industrial_gateway: dnp3
```

## Sequence

```plantuml
participant sensors
participant ieee738
participant mqtt_publisher
participant dnp3_outstation
queue mqtt_broker
participant industrial_gateway

sensors -> ieee738: temp + humidity + solar + rain
ieee738 -> mqtt_publisher: derived values
ieee738 -> dnp3_outstation: update analog input points
mqtt_publisher -> mqtt_broker: publish measurements
industrial_gateway -> dnp3_outstation: poll Group 30 + Group 1
```

## MQTT Topics Published

Per [ems/topic_structure_adr.md](../ems/topic_structure_adr.md). Payload is `FloatSample {ts, value}` unless noted.

- `sites/{site_id}/devices/{device_id}/measurements/conductor_temp/celsius`
- `sites/{site_id}/devices/{device_id}/measurements/ambient_temp/celsius`
- `sites/{site_id}/devices/{device_id}/measurements/humidity/percent`
- `sites/{site_id}/devices/{device_id}/measurements/solar_irradiance/watts_per_m2`
- `sites/{site_id}/devices/{device_id}/measurements/rain/none` — `BooleanSample`
- `sites/{site_id}/devices/{device_id}/measurements/dynamic_rating/amps` — derived per IEEE 738
- `sites/{site_id}/devices/{device_id}/measurements/status/none` — `EnumSample`, LWT-backed

## Project Structure
```
├── pyproject.toml           # Dependencies and build config
├── src/
│   ├── main.py              # Application entry point
│   ├── sensors/             # Sensor driver modules
│   ├── __init__.py
│   ├── thermal_camera/
│   │   ├── thermal_camera_client_test.py
│   │   ├── thermal_camera_client.py
│   │   ├── thermal_camera_driver.py
│   │   └── __init__.py
│   ├── temp_humidity_sensor/
│   │   ├── temp_humidity_sensor_client_test.py
│   │   ├── temp_humidity_sensor_client.py
│   │   ├── temp_humidity_sensor_driver.py
│   │   └── __init__.py
│   ├── uv_light_sensor/
│   │   ├── uv_light_sensor_client_test.py
│   │   ├── uv_light_sensor_client.py
│   │   ├── uv_light_sensor_driver.py
│   │   └── __init__.py
│   ├── rain_sensor/
│   │   ├── rain_sensor_client_test.py
│   │   ├── rain_sensor_client.py
│   │   ├── rain_sensor_driver.py
│   │   └── __init__.py
│   ├── ieee738.py           # IEEE 738 calculation engine
│   ├── ieee738_test.py      # Algorithm unit tests
│   ├── mqtt_client.py       # MQTT publisher
│   ├── mqtt_client_test.py  # MQTT client tests
│   └── config.py            # Configuration management
├── tests/
│   └── test_integration.py  # End-to-end integration tests
└── README.md                # This file
```

## Usage
```bash
uv run python src/main.py
```
