from pathlib import Path
import sys
import types

import numpy as np

from tests.utils.stubs import setup_stubs, load_module

ROOT = Path(__file__).resolve().parents[2]


def load_spectral_flux():
    setup_stubs()
    module = types.ModuleType("inputs.audio.core.audio_device_input")
    class AudioDeviceInput:  # pragma: no cover - placeholder for import
        pass
    module.AudioDeviceInput = AudioDeviceInput
    sys.modules["inputs.audio.core.audio_device_input"] = module
    return load_module("processing.spectral_flux", ROOT / "processing" / "spectral_flux.py")


class DummyAudio:
    def __init__(self, chunks):
        self.chunks = list(chunks)

    def peek(self):  # pragma: no cover - interface placeholder
        return self.chunks.pop(0) if self.chunks else None


def test_spectral_flux_basic() -> None:
    mod = load_spectral_flux()
    audio = DummyAudio([np.ones(8), np.zeros(8)])
    op = mod.SpectralFlux(audio)
    assert op.process() == 0.0
    assert op.process() > 0.0


def test_spectral_flux_edge_cases() -> None:
    mod = load_spectral_flux()
    assert mod.SpectralFlux(DummyAudio([None])).process() == 0.0
    assert mod.SpectralFlux(DummyAudio([np.array([])])).process() == 0.0

    audio = DummyAudio([np.ones((8, 2)), np.zeros((8, 2))])
    op = mod.SpectralFlux(audio)
    op.process()
    assert op.process() > 0.0
