"""Unit tests for IEEE 738 steady-state ampacity calc.

Test inputs + expected outputs are keyed to IEEE Std 738-2012 Annex A worked
examples. The simplifications taken in the implementation (solar geometry
fixed at zenith, film-property polynomial fits) introduce ~5-10% drift from
the textbook number; assertions use loose tolerances that still catch
implementation regressions.
"""

import math

import pytest

from src.ieee738 import (
    DRAKE_ACSR_795,
    convective_heat_loss,
    joule_heating,
    radiative_heat_loss,
    resistance_at_temp,
    solar_heat_gain,
    steady_state_current,
)

# ---------------------------------------------------------------------------
# Resistance temperature dependence
# ---------------------------------------------------------------------------


def test_resistance_at_25c_matches_reference() -> None:
    """At 25  degC, R(T_c) == the reference resistance."""
    actual = resistance_at_temp(DRAKE_ACSR_795, 25.0)
    assert actual == pytest.approx(DRAKE_ACSR_795.resistance_25c_ohm_per_m)


def test_resistance_rises_with_temperature() -> None:
    """Linear temp coefficient: R(100) > R(25) by alpha.d_T."""
    r_25 = resistance_at_temp(DRAKE_ACSR_795, 25.0)
    r_100 = resistance_at_temp(DRAKE_ACSR_795, 100.0)
    expected_ratio = 1.0 + DRAKE_ACSR_795.resistance_temp_coeff_per_c * 75.0
    assert r_100 / r_25 == pytest.approx(expected_ratio)


# ---------------------------------------------------------------------------
# Individual heat-balance terms
# ---------------------------------------------------------------------------


def test_joule_heating_is_quadratic_in_current() -> None:
    """q_j prop_to I^2 -- doubling current 4*s joule heating."""
    base = joule_heating(DRAKE_ACSR_795, 500.0, 75.0)
    doubled = joule_heating(DRAKE_ACSR_795, 1000.0, 75.0)
    assert doubled / base == pytest.approx(4.0)


def test_radiative_loss_zero_when_conductor_at_ambient() -> None:
    """q_r = 0 when T_c == T_a (Stefan-Boltzmann d_T^4 collapses to 0)."""
    actual = radiative_heat_loss(DRAKE_ACSR_795, 40.0, 40.0)
    assert actual == pytest.approx(0.0, abs=1e-9)


def test_radiative_loss_positive_when_conductor_hotter() -> None:
    """Conductor at 100  degC, ambient at 40  degC -> positive radiative loss."""
    actual = radiative_heat_loss(DRAKE_ACSR_795, 100.0, 40.0)
    assert actual > 0


def test_solar_gain_zero_when_no_irradiance() -> None:
    """No sun -> no solar heat gain."""
    assert solar_heat_gain(DRAKE_ACSR_795, 0.0) == pytest.approx(0.0)


def test_solar_gain_scales_with_irradiance() -> None:
    """Linear in solar irradiance."""
    q_500 = solar_heat_gain(DRAKE_ACSR_795, 500.0)
    q_1000 = solar_heat_gain(DRAKE_ACSR_795, 1000.0)
    assert q_1000 / q_500 == pytest.approx(2.0)


def test_convective_loss_zero_when_conductor_at_ambient() -> None:
    """Both forced + natural collapse to 0 at T_c == T_a."""
    actual = convective_heat_loss(DRAKE_ACSR_795, 40.0, 40.0, 0.61)
    assert actual == pytest.approx(0.0, abs=1e-3)


def test_convective_loss_grows_with_wind_speed() -> None:
    """Higher wind -> more forced convection cooling."""
    low = convective_heat_loss(DRAKE_ACSR_795, 100.0, 40.0, 0.5)
    high = convective_heat_loss(DRAKE_ACSR_795, 100.0, 40.0, 5.0)
    assert high > low


def test_wind_perpendicular_cools_more_than_parallel() -> None:
    """Wind angle phi=90 deg gives max cooling; phi=0 deg gives min (k_angle ~ 0.388)."""
    perpendicular = convective_heat_loss(
        DRAKE_ACSR_795, 100.0, 40.0, 5.0, wind_angle_deg=90.0
    )
    parallel = convective_heat_loss(
        DRAKE_ACSR_795, 100.0, 40.0, 5.0, wind_angle_deg=0.0
    )
    assert perpendicular > parallel


# ---------------------------------------------------------------------------
# Steady-state current -- IEEE 738 Annex A reference scenario
# ---------------------------------------------------------------------------


def test_drake_acsr_annex_a_worked_example_within_tolerance() -> None:
    """
    IEEE 738-2012 Annex A worked example:
      ACSR Drake 26/7 (795 kcmil)
      T_conductor = 100  degC
      T_ambient   = 40  degC
      V_wind      = 0.61 m/s perpendicular to conductor
      S_i         = 1000 W/m^2
      -> I_steady-state ~ 993 A

    Implementation simplifications (zenith solar, polynomial air-property
    fits) produce a 5-10% drift from the textbook number; loose tolerance
    still catches regressions in the heat-balance equations.
    """
    actual = steady_state_current(
        conductor=DRAKE_ACSR_795,
        conductor_temp_c=100.0,
        ambient_temp_c=40.0,
        wind_speed_mps=0.61,
        solar_irradiance_w_per_m2=1000.0,
        wind_angle_deg=90.0,
    )
    # Textbook answer: 993 A. Wider tolerance acknowledges simplifications.
    assert actual == pytest.approx(
        993.0, rel=0.15
    ), f"Annex A worked example: expected ~993 A, got {actual:.1f} A"


def test_steady_state_current_rises_with_wind() -> None:
    """At fixed conductor target temp, higher wind -> higher allowed current."""
    low_wind = steady_state_current(
        conductor=DRAKE_ACSR_795,
        conductor_temp_c=100.0,
        ambient_temp_c=40.0,
        wind_speed_mps=0.5,
        solar_irradiance_w_per_m2=1000.0,
    )
    high_wind = steady_state_current(
        conductor=DRAKE_ACSR_795,
        conductor_temp_c=100.0,
        ambient_temp_c=40.0,
        wind_speed_mps=5.0,
        solar_irradiance_w_per_m2=1000.0,
    )
    assert (
        high_wind > low_wind
    ), f"more wind should permit more current: low={low_wind:.0f} A, high={high_wind:.0f} A"


def test_steady_state_current_falls_with_ambient_heat() -> None:
    """Hotter ambient -> less headroom to T_c target -> lower current."""
    cool_day = steady_state_current(
        conductor=DRAKE_ACSR_795,
        conductor_temp_c=100.0,
        ambient_temp_c=20.0,
        wind_speed_mps=1.0,
        solar_irradiance_w_per_m2=1000.0,
    )
    hot_day = steady_state_current(
        conductor=DRAKE_ACSR_795,
        conductor_temp_c=100.0,
        ambient_temp_c=40.0,
        wind_speed_mps=1.0,
        solar_irradiance_w_per_m2=1000.0,
    )
    assert cool_day > hot_day


def test_steady_state_current_falls_with_solar_load() -> None:
    """More solar heat gain -> less net cooling available -> lower current."""
    overcast = steady_state_current(
        conductor=DRAKE_ACSR_795,
        conductor_temp_c=100.0,
        ambient_temp_c=40.0,
        wind_speed_mps=1.0,
        solar_irradiance_w_per_m2=200.0,
    )
    full_sun = steady_state_current(
        conductor=DRAKE_ACSR_795,
        conductor_temp_c=100.0,
        ambient_temp_c=40.0,
        wind_speed_mps=1.0,
        solar_irradiance_w_per_m2=1000.0,
    )
    assert overcast > full_sun


def test_steady_state_current_zero_when_solar_overwhelms_cooling() -> None:
    """If solar gain > q_c + q_r, no current can stay below T_c target."""
    actual = steady_state_current(
        conductor=DRAKE_ACSR_795,
        conductor_temp_c=40.0,  # target = ambient = no buffer
        ambient_temp_c=40.0,
        wind_speed_mps=0.0,  # no wind cooling
        solar_irradiance_w_per_m2=1000.0,  # strong solar gain
    )
    assert actual == 0.0


def test_pi_appears_in_calc() -> None:
    """Sanity: radiative term must use math.pi (cylinder circumference)."""
    # Indirect check -- at 100  degC / 40  degC the radiative loss should be
    # proportional to pi.D.eps.sigma.(T_c^4 - T_a^4).
    actual = radiative_heat_loss(DRAKE_ACSR_795, 100.0, 40.0)
    expected = (
        math.pi
        * DRAKE_ACSR_795.diameter_m
        * DRAKE_ACSR_795.emissivity
        * 5.6697e-8
        * ((100.0 + 273.15) ** 4 - (40.0 + 273.15) ** 4)
    )
    assert actual == pytest.approx(expected, rel=1e-4)
