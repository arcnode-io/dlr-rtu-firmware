"""compute_tick unit tests. The async run() is covered by integration tests."""

from build import Mode
from src.app import compute_tick
from src.sensor_suite import build_sensor_suite


def test_compute_tick_returns_positive_rating_and_limit() -> None:
    """Sim sensors at first-read state -> non-zero line rating + envelope."""
    suite = build_sensor_suite(Mode.LOCAL)
    line_rating_a, limit_w = compute_tick(suite)
    # First sim tick: low ambient (15C), low wind (0 m/s), zero solar -> some
    # ampacity available because conductor target (20C) > ambient.
    assert line_rating_a > 0.0
    assert limit_w > 0.0


def test_compute_tick_envelope_scales_with_line_rating() -> None:
    """DOE limit = V * I * sqrt3 -> bigger I means bigger watts."""
    suite = build_sensor_suite(Mode.LOCAL)
    # advance the sensors a few ticks to get a non-trivial rating
    for _ in range(5):
        compute_tick(suite)
    line_rating_a_later, limit_w_later = compute_tick(suite)
    # Ratio should match: limit_w / line_rating_a is a fixed multiplier.
    ratio_later = limit_w_later / line_rating_a_later
    assert ratio_later > 0.0
    # 138kV * sqrt(3) ~ 239 kV-equivalent => limit/I ~ 239000
    assert 230_000.0 < ratio_later < 250_000.0
