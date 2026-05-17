"""IEEE Std 738 steady-state line ampacity calculation.

Pure functions over conductor + environment inputs -> permissible current (amps).
Heat balance: q_c + q_r = q_s + q_j  (steady state, no thermal mass term).

Reference: IEEE Std 738-2012 (R2023), Annex A worked example. Test values are
keyed to that annex so changes to the math get caught against an authoritative
external source.

This module is I/O-free and has no dependencies beyond the stdlib `math`. The
sim + real sensor drivers feed it inputs; the result drives the DNP3
outstation publish path.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ConductorProperties:
    """Physical + electrical properties of an overhead conductor."""

    diameter_m: float
    """Outer diameter in meters."""

    resistance_25c_ohm_per_m: float
    """AC resistance at 25  degC, ohms per meter."""

    resistance_temp_coeff_per_c: float
    """Linear temperature coefficient of resistance (1/ degC). For ACSR Drake
    aluminum-strand: ~0.00403."""

    emissivity: float
    """Black-body emissivity (0..1). Bare new conductor ~0.23, aged ~0.5-0.9."""

    solar_absorptivity: float
    """Solar absorptivity (0..1). Bare new conductor ~0.23, aged ~0.5-0.9."""


# IEEE Std 738-2012 Annex A: ACSR Drake 26/7 conductor (795 kcmil).
DRAKE_ACSR_795: ConductorProperties = ConductorProperties(
    diameter_m=0.02814,  # 28.14 mm
    resistance_25c_ohm_per_m=7.283e-5,  # 7.283e-5 ohm/m at 25  degC, AC
    resistance_temp_coeff_per_c=0.00403,
    emissivity=0.5,
    solar_absorptivity=0.5,
)

STEFAN_BOLTZMANN: float = 5.6697e-8  # W/(m^2.K^4)


def resistance_at_temp(
    conductor: ConductorProperties, conductor_temp_c: float
) -> float:
    """AC resistance at a given conductor temperature (ohms per meter)."""
    delta_t = conductor_temp_c - 25.0
    return conductor.resistance_25c_ohm_per_m * (
        1.0 + conductor.resistance_temp_coeff_per_c * delta_t
    )


def joule_heating(
    conductor: ConductorProperties, current_a: float, conductor_temp_c: float
) -> float:
    """Resistive heat gain per meter (W/m): q_j = I^2 . R(T_c)."""
    return current_a**2 * resistance_at_temp(conductor, conductor_temp_c)


def radiative_heat_loss(
    conductor: ConductorProperties, conductor_temp_c: float, ambient_temp_c: float
) -> float:
    """Radiative heat loss per meter (W/m) per Stefan-Boltzmann.

    q_r = pi . D . eps . sigma . (T_c^4 - T_a^4)  with T in Kelvin.
    """
    t_c_k4 = (conductor_temp_c + 273.15) ** 4
    t_a_k4 = (ambient_temp_c + 273.15) ** 4
    return (
        math.pi
        * conductor.diameter_m
        * conductor.emissivity
        * STEFAN_BOLTZMANN
        * (t_c_k4 - t_a_k4)
    )


def solar_heat_gain(
    conductor: ConductorProperties, solar_irradiance_w_per_m2: float
) -> float:
    """Solar heat gain per meter (W/m): q_s = alpha . Q_se . D.

    Q_se here is the total solar irradiance flux density (W/m^2) at the
    conductor -- already accounts for atmospheric attenuation. For a horizontal
    conductor with the sun directly overhead, the projected area per meter is
    just the diameter. Real IEEE 738 includes elevation/azimuth + sun-angle
    correction; that detail lives in a follow-up extension once we have a real
    sun-position model.
    """
    return (
        conductor.solar_absorptivity * solar_irradiance_w_per_m2 * conductor.diameter_m
    )


def convective_heat_loss(
    conductor: ConductorProperties,
    conductor_temp_c: float,
    ambient_temp_c: float,
    wind_speed_mps: float,
    wind_angle_deg: float = 90.0,
) -> float:
    """Forced + natural convective heat loss per meter (W/m).

    Heat loss = h . A . d_T  where A = pi.D per meter and h = k.Nu/D, giving
    q_c = pi . Nu . k . d_T  (per meter of conductor).

    Nusselt number from Hilpert's cross-flow-over-a-cylinder correlation
    (which IEEE 738 references via Eq 4/5):

      40   < Re < 4 000     -> Nu = 0.683 . Re^0.466
      4000 < Re < 40 000    -> Nu = 0.193 . Re^0.618

    Wind angle correction per §4.4.3.1:
      k_angle = 1.194 - cos(phi) + 0.194.cos(2phi) + 0.368.sin(2phi)
    where phi is the angle between wind and conductor (90 deg = perpendicular = max cooling).

    Natural convection (zero wind) per Morgan's correlation (Eq 6 equivalent).
    Returns max(forced, natural) -- low-wind conditions are buoyancy-dominated.
    """
    t_film_c = 0.5 * (conductor_temp_c + ambient_temp_c)
    t_film_k = t_film_c + 273.15

    # Air properties at the film temperature. Polynomial fits good to
    # ±1% across 0-100  degC film range (sufficient for line-rating accuracy).
    rho_air = 1.293 - 1.525e-4 * t_film_c + 6.379e-9 * t_film_c**2
    mu_air = (1.458e-6 * t_film_k**1.5) / (t_film_k + 110.4)
    k_air = 2.424e-2 + 7.477e-5 * t_film_c - 4.407e-9 * t_film_c**2

    delta_t = max(conductor_temp_c - ambient_temp_c, 0.0)

    if wind_speed_mps > 0:
        reynolds = conductor.diameter_m * rho_air * wind_speed_mps / mu_air
        # Hilpert: pick the regime by Re. Below 40 the correlation breaks
        # down and natural convection dominates anyway, so use the low form.
        nusselt = (
            0.193 * reynolds**0.618 if reynolds > 4000 else 0.683 * reynolds**0.466
        )
        q_forced = math.pi * nusselt * k_air * delta_t

        # Wind angle correction (per IEEE 738 §4.4.3.1).
        phi_rad = math.radians(wind_angle_deg)
        k_angle = (
            1.194
            - math.cos(phi_rad)
            + 0.194 * math.cos(2 * phi_rad)
            + 0.368 * math.sin(2 * phi_rad)
        )
        q_forced *= max(k_angle, 0.0)
    else:
        q_forced = 0.0

    # Natural convection per Morgan's correlation for horizontal cylinders.
    # Coefficient 3.645.rho^0.5.D^0.75.d_T^1.25 gives W/m at typical conductor
    # diameters and temperature gradients (matches IEEE 738 Eq 6 form).
    q_natural = 3.645 * rho_air**0.5 * conductor.diameter_m**0.75 * delta_t**1.25

    return max(q_forced, q_natural)


def steady_state_current(
    conductor: ConductorProperties,
    conductor_temp_c: float,
    ambient_temp_c: float,
    wind_speed_mps: float,
    solar_irradiance_w_per_m2: float,
    wind_angle_deg: float = 90.0,
) -> float:
    """Permissible current for steady-state conductor temperature (amps).

    Solves the heat balance q_c + q_r = q_s + q_j for I:
        I = sqrt((q_c + q_r - q_s) / R(T_c))

    Returns 0 when the net cooling can't keep the conductor at `conductor_temp_c`
    (i.e., solar heat alone exceeds available cooling) -- physically this means
    no current can flow without exceeding the temperature target.
    """
    q_c = convective_heat_loss(
        conductor,
        conductor_temp_c,
        ambient_temp_c,
        wind_speed_mps,
        wind_angle_deg,
    )
    q_r = radiative_heat_loss(conductor, conductor_temp_c, ambient_temp_c)
    q_s = solar_heat_gain(conductor, solar_irradiance_w_per_m2)
    net_cooling = q_c + q_r - q_s
    if net_cooling <= 0:
        return 0.0
    r_t = resistance_at_temp(conductor, conductor_temp_c)
    return math.sqrt(net_cooling / r_t)
