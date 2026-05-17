"""Unit tests for Dnp3Outstation — patches OutStationApplication so tests
don't bind a real TCP port. End-to-end (real master polls real outstation)
is covered by integration tests."""

from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest

from src.dnp3_outstation import (
    IDX_DYNAMIC_LINE_RATING,
    IDX_EXPORT_LIMIT,
    IDX_IMPORT_LIMIT,
    IDX_LR_STATUS,
    IDX_OE_STATUS,
    NUM_ANALOG_POINTS,
    STATUS_COMM_FAIL,
    Dnp3Outstation,
)

AppMock = tuple[MagicMock, MagicMock]


@pytest.fixture
def app_mock() -> Iterator[AppMock]:
    """Patch OutStationApplication at the import site in dnp3_outstation."""
    with patch("src.dnp3_outstation.OutStationApplication") as cls_mock:
        instance = MagicMock()
        cls_mock.return_value = instance
        yield cls_mock, instance


def test_constructor_passes_addresses_to_outstation_application(
    app_mock: AppMock,
) -> None:
    """Constructor wires IP, port, and link-layer addresses through to opendnp3."""
    # Arrange
    cls_mock, _ = app_mock
    # Act
    Dnp3Outstation(
        outstation_ip="127.0.0.1",
        port=20001,
        master_addr=3,
        outstation_addr=7,
    )
    # Assert
    cls_mock.assert_called_once_with(
        outstation_ip="127.0.0.1",
        port=20001,
        master_id=3,
        outstation_id=7,
        numAnalog=NUM_ANALOG_POINTS,
    )


def test_publish_envelope_updates_two_analog_points(app_mock: AppMock) -> None:
    """DOE limits (opModImpLimW/opModExpLimW) land at canonical indices 0 + 1."""
    # Arrange
    _, instance = app_mock
    out = Dnp3Outstation()
    # Act
    out.publish_envelope(import_limit_w=5_000_000.0, export_limit_w=2_500_000.0)
    # Assert — analog_input updates at the canonical indices
    assert instance.apply_update_analog_input.call_args_list == [
        ((5_000_000.0, IDX_IMPORT_LIMIT),),
        ((2_500_000.0, IDX_EXPORT_LIMIT),),
    ]


def test_publish_line_rating_updates_dynamic_index(app_mock: AppMock) -> None:
    """IEEE 738 dynamic line rating lands at canonical index 10."""
    # Arrange
    _, instance = app_mock
    out = Dnp3Outstation()
    # Act
    out.publish_line_rating(dynamic_amps=850.0)
    # Assert
    instance.apply_update_analog_input.assert_called_once_with(
        850.0, IDX_DYNAMIC_LINE_RATING
    )


def test_publish_status_writes_both_status_points(app_mock: AppMock) -> None:
    """OE + LR status enums land at canonical indices 100 + 101 as analog."""
    # Arrange
    _, instance = app_mock
    out = Dnp3Outstation()
    # Act — OE is healthy, LR has lost comms
    out.publish_status(oe_status=0, lr_status=STATUS_COMM_FAIL)
    # Assert — both updates emit as analog (Q-B: 4-value enum doesn't fit a bit)
    assert instance.apply_update_analog_input.call_args_list == [
        ((0.0, IDX_OE_STATUS),),
        ((float(STATUS_COMM_FAIL), IDX_LR_STATUS),),
    ]


def test_lifecycle_delegates_to_underlying_app(app_mock: AppMock) -> None:
    """start/shutdown forward to the underlying OutStationApplication."""
    # Arrange
    _, instance = app_mock
    out = Dnp3Outstation()
    # Act
    out.start()
    out.shutdown()
    # Assert
    instance.start.assert_called_once()
    instance.shutdown.assert_called_once()
