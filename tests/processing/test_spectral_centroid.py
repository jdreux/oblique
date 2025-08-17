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


def test_spectral_centroid_branches() -> None:
    setup_stubs()
    mod = load_module("processing.spectral_centroid", ROOT / "processing" / "spectral_centroid.py")

    sr = 44100
    t = np.arange(sr // 100) / sr

    def make(freq: float, stereo: bool = False) -> np.ndarray:
        sig = np.sin(2 * np.pi * freq * t).astype(np.float32)
        return np.stack([sig, sig], axis=1) if stereo else sig

    op = mod.SpectralCentroid(DummyInput(make(500, stereo=True)))
    val = op.process()
    assert 0.0 <= val < 0.3

    op = mod.SpectralCentroid(DummyInput(make(3000)))
    val = op.process()
    assert 0.3 <= val < 0.6

    op = mod.SpectralCentroid(DummyInput(make(6000)))
    val = op.process()
    assert 0.6 <= val <= 1.0

    op = mod.SpectralCentroid(DummyInput(make(10000)))
    assert op.process() > 0.0

