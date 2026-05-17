"""DOE (Dynamic Operating Envelope) derivation from line rating.

Pure function: converts IEEE 738 line ampacity (amps) to a permissible
import / export power envelope (watts) at the point of interconnection.

For a 3-phase transmission tie:
    P_max_W = V_line_to_line_V * I_amps * sqrt3 * power_factor

We assume `power_factor = 1.0` for the envelope-limit calculation -- utilities
publish envelopes as rated active-power limits at unity PF. Reactive headroom
is a separate concern.

Symmetric envelope (import_limit_w == export_limit_w == P_max_W) is the
default. Asymmetric envelopes (e.g., distribution circuit with limited
back-feed capability) come from a utility-published policy multiplier; for
now we keep the simple symmetric form and let CSIP-AUS override land later.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class OperatingEnvelope:
    """DOE result -- symmetric watts limit derived from IEEE 738 ampacity."""

    import_limit_w: float
    """Maximum power flow from grid -> site (watts)."""

    export_limit_w: float
    """Maximum power flow from site -> grid (watts)."""


def derive_envelope(
    line_rating_a: float,
    v_line_to_line_kv: float,
    power_factor: float = 1.0,
    export_asymmetry: float = 1.0,
) -> OperatingEnvelope:
    """Derive the operating envelope from a line ampacity rating.

    Args:
        line_rating_a: IEEE 738 steady-state current rating (amps).
        v_line_to_line_kv: Nominal line-to-line voltage at the POI (kV).
            138 kV = typical sub-transmission tie; 12.47 kV = typical
            primary distribution; 480 V = service drop.
        power_factor: 0..1, defaults to 1.0 (active power envelope).
        export_asymmetry: 0..1 multiplier applied to export-side limit;
            defaults to 1.0 (symmetric). Set <1.0 when the utility allows
            less back-feed than import -- e.g., a distribution circuit with
            limited reverse-power tolerance.

    Returns:
        OperatingEnvelope with import_limit_w + export_limit_w in watts.
    """
    v_line_v = v_line_to_line_kv * 1000.0
    p_max_w = v_line_v * line_rating_a * math.sqrt(3.0) * power_factor
    return OperatingEnvelope(
        import_limit_w=p_max_w,
        export_limit_w=p_max_w * max(min(export_asymmetry, 1.0), 0.0),
    )
