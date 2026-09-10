"""Sawtooth simulator + sensor Protocol.

Sawtooth pattern matches the ARCNODE canonical sim approach used in
`ems-industrial-fixtures` (mock-modbus-server etc.) -- value sweeps min->max
by step, wraps when it overflows. Deterministic, easy to assert against, and
exercises the full value range over time so downstream code sees realistic
movement on every wire it touches.
"""

from __future__ import annotations


class SawtoothSim:
    """Deterministic single-value sawtooth driver.

    Each `read()` returns the current value AND advances the internal cursor
    by `step`. When the cursor passes `max`, it wraps to `min`. Pure state +
    deterministic — easy to unit test against an expected step sequence.
    """

    def __init__(
        self,
        *,
        min_value: float,
        max_value: float,
        step: float,
        start: float | None = None,
    ) -> None:
        """Configure the sawtooth.

        Args:
            min_value: Lower bound (inclusive); wrap target after overflow.
            max_value: Upper bound (exclusive overflow).
            step: Increment applied AFTER each read.
            start: Initial value; defaults to `min_value` when omitted.
        """
        if min_value >= max_value:
            raise ValueError(
                f"min_value ({min_value}) must be < max_value ({max_value})"
            )
        if step <= 0:
            raise ValueError(f"step ({step}) must be > 0")
        self._min = min_value
        self._max = max_value
        self._step = step
        self._value = start if start is not None else min_value

    def read(self) -> float:
        """Return current value, then advance + wrap."""
        value = self._value
        self._value += self._step
        if self._value > self._max:
            self._value = self._min
        return value


class ConstantSim:
    """Fixed-value driver -- always returns the same reading.

    Reason: for a live demo where one sensor (e.g. DHT) is real hardware
    being manipulated on camera, a sawtooth on every other IEEE 738 input
    swamps the signal -- rating moves every tick regardless of what's being
    demonstrated. Hold everything else steady so the real input is the only
    thing moving.
    """

    def __init__(self, value: float) -> None:
        """Configure with the fixed value every read() returns."""
        self._value = value

    def read(self) -> float:
        """Return the fixed value -- never advances."""
        return self._value
