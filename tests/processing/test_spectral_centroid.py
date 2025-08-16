from pathlib import Path

import numpy as np

from tests.utils.stubs import setup_stubs, load_module


ROOT = Path(__file__).resolve().parents[2]


class DummyInput:
    def __init__(self, data):
        self._data = data

    def peek(self):  # pragma: no cover - signature placeholder
        return self._data


def test_spectral_centroid_basic() -> None:
    setup_stubs()
    mod = load_module("processing.spectral_centroid", ROOT / "processing" / "spectral_centroid.py")

    sr = 44100
    t = np.arange(sr // 100) / sr
    signal = np.sin(2 * np.pi * 4000 * t).astype(np.float32)
    op = mod.SpectralCentroid(DummyInput(signal))
    assert 0.0 < op.process() <= 1.0

    assert mod.SpectralCentroid(DummyInput(None)).process() == 0.0
    assert mod.SpectralCentroid(DummyInput(np.array([]))).process() == 0.0

