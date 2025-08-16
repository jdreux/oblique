from pathlib import Path

import numpy as np
import pytest

from tests.utils.stubs import setup_stubs, load_module


ROOT = Path(__file__).resolve().parents[2]


class DummyInput:
    def __init__(self, data):
        self._data = data

    def peek(self, channels=None):  # pragma: no cover - signature placeholder
        return self._data


def test_normalized_amplitude_curves() -> None:
    setup_stubs()
    mod = load_module("processing.normalized_amplitude", ROOT / "processing" / "normalized_amplitude.py")

    data = np.ones((4, 1), dtype=np.float32) * 0.5

    op = mod.NormalizedAmplitudeOperator(DummyInput(data))
    assert 0.0 < op.process() <= 1.0

    for curve in (
        mod.CurveType.SQRT,
        mod.CurveType.LOG,
        mod.CurveType.SIGMOID,
    ):
        op = mod.NormalizedAmplitudeOperator(DummyInput(data), curve=curve)
        assert op.process() > 0.0

    op = mod.NormalizedAmplitudeOperator(DummyInput(None))
    assert op.process() == 0.0

    op = mod.NormalizedAmplitudeOperator(DummyInput("bad"))
    with pytest.raises(ValueError):
        op.process()

