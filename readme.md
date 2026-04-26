# EMS Line Controller DLR 🌡️📈

![](https://img.shields.io/gitlab/pipeline-status/arcnode-io/ems-line-controller-dlr?branch=main&logo=gitlab)
![](https://gitlab.com/arcnode-io/ems-line-controller-dlr/badges/main/coverage.svg)
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

## Core Algorithm

Dynamic rating calculation using IEEE 738 standard:

$$ P_{max} = \frac{(T_{max} - T_{amb} - ΔT_{solar} + ΔT_{rain})}{R_{thermal}} $$

Where:
- Conductor max temp (80°C): $T_{max}$
- DHT22 reading: $T_{amb}$
- SI1145 radiation factor: $ΔT_{solar}$
- YL-83 cooling coefficient: $ΔT_{rain}$
- FLIR Lepton thermal resistance: $R_{thermal} = \frac{(T_{conductor} - T_{ambient})}{P_{current}}$

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
