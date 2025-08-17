from pathlib import Path

import numpy as np

from tests.utils.stubs import setup_stubs, load_module

ROOT = Path(__file__).resolve().parents[2]


class DummyAudio:
    def __init__(self, chunks, sample_rate: int = 48000) -> None:
        self.chunks = list(chunks)
        self.sample_rate = sample_rate

    def peek(self, n_buffers: int = 1, channels=None):  # pragma: no cover - interface placeholder
        return self.chunks.pop(0) if self.chunks else None


def test_fft_bands_basic() -> None:
    setup_stubs()
    mod = load_module("processing.fft_bands", ROOT / "processing" / "fft_bands.py")

    chunks = [
        np.array([], dtype=np.float32),
        np.ones((4, 2), dtype=np.float32),
        np.ones(10, dtype=np.float32),
        np.ones(8, dtype=np.float32) * 2,
    ]
    audio = DummyAudio(chunks)
    fft = mod.FFTBands(audio, n_fft=8, num_bands=4, smoothing_factor=0.5)

    assert fft.process() == [0.0] * 4  # empty chunk
    assert fft.process() == [0.0] * 4  # still filling buffer
    res = fft.process()
    assert len(res) == 4 and all(0.0 <= v <= 1.0 for v in res)
    res2 = fft.process()
    assert len(res2) == 4 and all(0.0 <= v <= 1.0 for v in res2)


def test_fft_bands_missing_audio() -> None:
    setup_stubs()
    mod = load_module("processing.fft_bands", ROOT / "processing" / "fft_bands.py")

    audio = DummyAudio([None])
    fft = mod.FFTBands(audio, n_fft=8, num_bands=2)
    assert fft.process() == [0.0, 0.0]
