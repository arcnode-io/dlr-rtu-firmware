"""Local DNP3 master ↔ outstation integration test.

Spins up our `Dnp3Outstation`, publishes known values, then connects a real
`MasterApplication` from `dnp3_python` and verifies the master can read the
published values back. Validates the full opendnp3 wire path end-to-end.

NOT parallelizable — opendnp3 spawns its own threads and the master+outstation
share a single TCP port + fixed link-layer addresses. Run with `-p no:xdist`
or single-worker mode if pytest-xdist is involved.
"""

import logging
import time

import pytest
from dnp3_python.dnp3station.master import MasterApplication

from src.dnp3_outstation import (
    IDX_EXPORT_LIMIT,
    IDX_IMPORT_LIMIT,
    Dnp3Outstation,
)

# Reason: integration tests bind real ports — pick a high one out of the
# IANA-reserved DNP3 range (20000) to avoid collisions with prod outstations
# on the dev machine.
TEST_PORT = 21001
MASTER_ADDR = 2
OUTSTATION_ADDR = 1

# DNP3 master scan + response settles slowly — opendnp3 retries integrity
# polls + has 5s default per-task timeout. Conservative wait avoids flakes.
SESSION_SETTLE_SEC = 3.0
SCAN_SETTLE_SEC = 3.0

# Static analog variation the outstation database is configured for (Group 30
# Var 1 = 32-bit with flag — opendnp3 default). Master `get_val_by_*` reads
# the same variation the responder published.
ANALOG_GROUP = 30
ANALOG_VARIATION = 1


@pytest.fixture
def quiet_dnp3_logs() -> None:
    """opendnp3 is chatty at INFO; quiet for test runs."""
    logging.getLogger("dnp3").setLevel(logging.WARNING)


def test_master_reads_envelope_values_published_by_outstation(
    quiet_dnp3_logs: None,  # noqa: ARG001 — fixture configures global logger
) -> None:
    """Master polls outstation; published import/export limits round-trip end-to-end."""
    # Arrange — outstation publishes a known envelope before master connects
    outstation = Dnp3Outstation(
        outstation_ip="127.0.0.1",
        port=TEST_PORT,
        master_addr=MASTER_ADDR,
        outstation_addr=OUTSTATION_ADDR,
    )
    outstation.start()
    expected_import = 5_000_000.0
    expected_export = 2_500_000.0
    master: MasterApplication | None = None
    try:
        outstation.publish_envelope(
            import_limit_w=expected_import, export_limit_w=expected_export
        )
        # Give opendnp3 a moment to commit the update into its DB.
        time.sleep(0.5)

        # Act — start master, wait for session, request scan, wait for response
        master = MasterApplication(
            master_ip="0.0.0.0",  # noqa: S104 — opendnp3 master binds locally
            outstation_ip="127.0.0.1",
            port=TEST_PORT,
            master_id=MASTER_ADDR,
            outstation_id=OUTSTATION_ADDR,
        )
        master.start()
        time.sleep(SESSION_SETTLE_SEC)
        master.send_scan_all_request()
        time.sleep(SCAN_SETTLE_SEC)

        # Assert — master's local DB has the values the outstation published.
        # Loose epsilon because opendnp3 may coerce the int32-with-flag wire
        # representation into a slightly different float on the master side.
        import_val = master.my_master.get_val_by_group_variation_index(
            group=ANALOG_GROUP, variation=ANALOG_VARIATION, index=IDX_IMPORT_LIMIT
        )
        export_val = master.my_master.get_val_by_group_variation_index(
            group=ANALOG_GROUP, variation=ANALOG_VARIATION, index=IDX_EXPORT_LIMIT
        )
        assert import_val is not None, "master never received import_limit"
        assert export_val is not None, "master never received export_limit"
        assert (
            abs(float(import_val) - expected_import) < 1.0
        ), f"import_limit drift: got {import_val}, expected {expected_import}"
        assert (
            abs(float(export_val) - expected_export) < 1.0
        ), f"export_limit drift: got {export_val}, expected {expected_export}"
    finally:
        if master is not None:
            master.shutdown()
        outstation.shutdown()
