"""DNP3 outstation publisher for IEEE 738 + DOE derived values.

Wraps `dnp3_python.dnp3station.outstation.OutStationApplication` so the rest
of the app talks to a small, opinionated interface and the underlying
opendnp3 lifecycle (start/stop/point updates) is encapsulated.

DNP3 point layout matches `edp-api/device_templates/leaf/operating_envelope.yaml`
+ `line_rating.yaml` (handoff Q2 reservations):
    - Group 30 AnalogInput index 0  -> import_limit  (watts, IEEE 2030.5 opModImpLimW)
    - Group 30 AnalogInput index 1  -> export_limit  (watts, IEEE 2030.5 opModExpLimW)
    - Group 30 AnalogInput index 10 -> dynamic_line_rating  (amps, IEEE 738)
    - Group 30 AnalogInput index 100 -> operating_envelope status  (enum)
    - Group 30 AnalogInput index 101 -> line_rating status  (enum)

Status is emitted as analog (not binary) per Q-B — 4-value enum doesn't fit
a single bit.
"""

import logging
from typing import Final

from dnp3_python.dnp3station.outstation import OutStationApplication

_log = logging.getLogger(__name__)

# Point-index constants — keep in sync with the edp-api leaf templates.
IDX_IMPORT_LIMIT: Final[int] = 0
IDX_EXPORT_LIMIT: Final[int] = 1
IDX_DYNAMIC_LINE_RATING: Final[int] = 10
IDX_OE_STATUS: Final[int] = 100
IDX_LR_STATUS: Final[int] = 101

# Outstation database must reserve at least IDX_LR_STATUS+1 analog slots.
NUM_ANALOG_POINTS: Final[int] = IDX_LR_STATUS + 1

# Status enum values (mirror operating_envelope.yaml + line_rating.yaml values:).
STATUS_OK: Final[int] = 0
STATUS_STALE: Final[int] = 1
STATUS_INVALID: Final[int] = 2
STATUS_COMM_FAIL: Final[int] = 3


class Dnp3Outstation:
    """Lifecycle + point-update facade over `OutStationApplication`."""

    def __init__(
        self,
        *,
        outstation_ip: str = "0.0.0.0",  # noqa: S104 nosec B104 — DNP3 outstation must listen on all interfaces
        port: int = 20000,
        master_addr: int = 2,
        outstation_addr: int = 1,
    ) -> None:
        """Configure the underlying opendnp3 outstation; not started yet.

        Args:
            outstation_ip: bind address. "0.0.0.0" listens on all interfaces.
            port: TCP port for the DNP3 master to connect to (default 20000).
            master_addr: DNP3 link-layer address of the master (gateway side).
            outstation_addr: DNP3 link-layer address of THIS outstation.
        """
        # Reason: opendnp3.DatabaseSizes requires all 8 point counts; passing
        # None for the unused ones blows up at session-open. Provide explicit
        # zeros for binary + analog output status; analog gets our reservation.
        self._app = OutStationApplication(
            outstation_ip=outstation_ip,
            port=port,
            master_id=master_addr,
            outstation_id=outstation_addr,
            numBinary=0,
            numBinaryOutputStatus=0,
            numAnalog=NUM_ANALOG_POINTS,
            numAnalogOutputStatus=0,
        )

    def start(self) -> None:
        """Open the TCP listener + begin responding to master polls."""
        self._app.start()
        _log.info("dnp3 outstation started")

    def shutdown(self) -> None:
        """Close TCP listener + free underlying opendnp3 channels."""
        self._app.shutdown()
        _log.info("dnp3 outstation stopped")

    def publish_envelope(self, import_limit_w: float, export_limit_w: float) -> None:
        """Update the DOE limit points the gateway polls.

        Args:
            import_limit_w: opModImpLimW (utility-allowed import in watts).
            export_limit_w: opModExpLimW (utility-allowed export in watts).
        """
        self._app.apply_update_analog_input(import_limit_w, IDX_IMPORT_LIMIT)
        self._app.apply_update_analog_input(export_limit_w, IDX_EXPORT_LIMIT)

    def publish_line_rating(self, dynamic_amps: float) -> None:
        """Update the IEEE 738 dynamic line rating point (amps)."""
        self._app.apply_update_analog_input(dynamic_amps, IDX_DYNAMIC_LINE_RATING)

    def publish_status(
        self, oe_status: int = STATUS_OK, lr_status: int = STATUS_OK
    ) -> None:
        """Update the per-producer status enums (0=OK,1=STALE,2=INVALID,3=COMM_FAIL)."""
        self._app.apply_update_analog_input(float(oe_status), IDX_OE_STATUS)
        self._app.apply_update_analog_input(float(lr_status), IDX_LR_STATUS)
