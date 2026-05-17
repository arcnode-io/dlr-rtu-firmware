"""Unit tests for Dnp3Outstation wrapper.

Patches AsyncOutstation at the import site so tests don't bind a real TCP port.
End-to-end (real master polls real outstation) is covered by integration tests.
"""

from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.dnp3_outstation import (
    IDX_DYNAMIC_LINE_RATING,
    IDX_EXPORT_LIMIT,
    IDX_IMPORT_LIMIT,
    IDX_LR_STATUS,
    IDX_OE_STATUS,
    STATUS_COMM_FAIL,
    Dnp3Outstation,
)

AppMock = tuple[MagicMock, MagicMock]


@pytest.fixture
def app_mock() -> Iterator[AppMock]:
    """Patch AsyncOutstation at the import site in src.dnp3_outstation."""
    with patch("src.dnp3_outstation.AsyncOutstation") as cls_mock:
        instance = MagicMock()
        instance.start = AsyncMock()
        instance.shutdown = AsyncMock()
        cls_mock.return_value = instance
        yield cls_mock, instance


def test_constructor_passes_addresses_to_async_outstation(app_mock: AppMock) -> None:
    """Constructor wires host, port, and link-layer addresses through."""
    cls_mock, _ = app_mock
    Dnp3Outstation(
        outstation_ip="127.0.0.1",
        port=20001,
        master_addr=3,
        outstation_addr=7,
    )
    cls_mock.assert_called_once_with(
        host="127.0.0.1",
        port=20001,
        master_addr=3,
        outstation_addr=7,
    )


def test_publish_envelope_updates_two_analog_points(app_mock: AppMock) -> None:
    """DOE limits (opModImpLimW/opModExpLimW) land at canonical indices 0 + 1."""
    _, instance = app_mock
    out = Dnp3Outstation()
    out.publish_envelope(import_limit_w=5_000_000.0, export_limit_w=2_500_000.0)
    assert instance.set_analog.call_args_list == [
        ((IDX_IMPORT_LIMIT, 5_000_000.0),),
        ((IDX_EXPORT_LIMIT, 2_500_000.0),),
    ]


def test_publish_line_rating_updates_dynamic_index(app_mock: AppMock) -> None:
    """IEEE 738 dynamic line rating lands at canonical index 10."""
    _, instance = app_mock
    out = Dnp3Outstation()
    out.publish_line_rating(dynamic_amps=850.0)
    instance.set_analog.assert_called_once_with(IDX_DYNAMIC_LINE_RATING, 850.0)


def test_publish_status_writes_both_status_points(app_mock: AppMock) -> None:
    """OE + LR status enums land at canonical indices 100 + 101 as analog."""
    _, instance = app_mock
    out = Dnp3Outstation()
    out.publish_status(oe_status=0, lr_status=STATUS_COMM_FAIL)
    assert instance.set_analog.call_args_list == [
        ((IDX_OE_STATUS, 0.0),),
        ((IDX_LR_STATUS, float(STATUS_COMM_FAIL)),),
    ]


@pytest.mark.asyncio
async def test_lifecycle_delegates_to_underlying_app(app_mock: AppMock) -> None:
    """start/shutdown forward to the underlying AsyncOutstation."""
    _, instance = app_mock
    out = Dnp3Outstation()
    await out.start()
    await out.shutdown()
    instance.start.assert_awaited_once()
    instance.shutdown.assert_awaited_once()
