"""HIL integration test. Validates real DHT22 hardware via DhtReal.

Runs on the Pi (which has GPIO + adafruit_dht). Other CI runners skip it
because adafruit_dht imports fail without board.D4 etc.
"""

import time

import pytest

from src.sensors.dht import DhtReading


def test_dht_real_reads_plausible_ambient() -> None:
    """Real DHT22 returns a reading in plausible indoor range."""
    pytest.importorskip("adafruit_dht")
    pytest.importorskip("board")
    from src.sensors.dht import DhtReal

    sensor = DhtReal()

    # Reason: the DHT22 bit-bang line is inherently flaky on a Pi 5 — a single
    # cold read fails often. DhtReal.read() is a thin single-shot wrapper by
    # design; the caller retries (datasheet minimum is 2s between reads).
    reading: DhtReading | None = None
    for _ in range(10):
        try:
            reading = sensor.read()
            break
        except RuntimeError:
            time.sleep(2.5)
    assert reading is not None, "DHT22 gave no valid reading in 10 attempts"

    # plausible indoor air: 10..40 C, 10..90% RH
    assert 10.0 <= reading.temperature_c <= 40.0
    assert 10.0 <= reading.humidity_percent <= 90.0
