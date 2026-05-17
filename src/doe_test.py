"""Unit tests for DOE derivation."""

import math

import pytest

from src.doe import OperatingEnvelope, derive_envelope


def test_138kv_1000a_yields_239_mw_symmetric() -> None:
    """Sub-transmission tie: 138 kV * 1000 A * sqrt3 ~ 239 MW symmetric envelope."""
    actual = derive_envelope(line_rating_a=1000.0, v_line_to_line_kv=138.0)
    expected_w = 138_000.0 * 1000.0 * math.sqrt(3.0)
    assert actual.import_limit_w == pytest.approx(expected_w)
    assert actual.export_limit_w == pytest.approx(expected_w)


def test_distribution_12_47kv_400a_yields_8_6_mw() -> None:
    """Primary distribution: 12.47 kV * 400 A * sqrt3 ~ 8.64 MW."""
    actual = derive_envelope(line_rating_a=400.0, v_line_to_line_kv=12.47)
    expected_w = 12_470.0 * 400.0 * math.sqrt(3.0)
    assert actual.import_limit_w == pytest.approx(expected_w)


def test_export_asymmetry_scales_export_only() -> None:
    """asymmetry=0.5 halves export, leaves import alone."""
    actual = derive_envelope(
        line_rating_a=1000.0, v_line_to_line_kv=138.0, export_asymmetry=0.5
    )
    assert actual.export_limit_w == pytest.approx(actual.import_limit_w * 0.5)


def test_export_asymmetry_clamps_above_1() -> None:
    """Capping asymmetry at 1.0 (export <= import) is a safety invariant."""
    actual = derive_envelope(
        line_rating_a=1000.0, v_line_to_line_kv=138.0, export_asymmetry=2.0
    )
    assert actual.export_limit_w == pytest.approx(actual.import_limit_w)


def test_export_asymmetry_clamps_below_0() -> None:
    """Negative asymmetry collapses to 0 (no export permitted)."""
    actual = derive_envelope(
        line_rating_a=1000.0, v_line_to_line_kv=138.0, export_asymmetry=-0.5
    )
    assert actual.export_limit_w == 0.0


def test_power_factor_scales_envelope() -> None:
    """PF=0.9 reduces both import + export by 10%."""
    pf_1 = derive_envelope(1000.0, 138.0, power_factor=1.0)
    pf_09 = derive_envelope(1000.0, 138.0, power_factor=0.9)
    assert pf_09.import_limit_w == pytest.approx(pf_1.import_limit_w * 0.9)
    assert pf_09.export_limit_w == pytest.approx(pf_1.export_limit_w * 0.9)


def test_zero_current_yields_zero_envelope() -> None:
    """No current -> no envelope."""
    actual = derive_envelope(line_rating_a=0.0, v_line_to_line_kv=138.0)
    assert actual == OperatingEnvelope(import_limit_w=0.0, export_limit_w=0.0)


def test_envelope_dataclass_is_frozen() -> None:
    """OperatingEnvelope is immutable so consumers can't tamper after derivation."""
    env = derive_envelope(1000.0, 138.0)
    with pytest.raises((AttributeError, TypeError)):
        env.import_limit_w = 0  # ty: ignore[invalid-assignment]
