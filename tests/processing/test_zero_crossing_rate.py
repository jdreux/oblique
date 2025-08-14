import importlib.util
import sys
import types
from pathlib import Path

import numpy as np


def load_zero_crossing_rate():
    inputs_pkg = types.ModuleType("inputs")
    sys.modules.setdefault("inputs", inputs_pkg)
    audio_module = types.ModuleType("inputs.audio_device_input")

    class AudioDeviceInput:  # pragma: no cover - placeholder for import
        pass

    audio_module.AudioDeviceInput = AudioDeviceInput
    sys.modules["inputs.audio_device_input"] = audio_module

    processing_pkg = types.ModuleType("processing")
    sys.modules.setdefault("processing", processing_pkg)
    base_module = types.ModuleType("processing.base_processing_operator")

    class BaseProcessingOperator:  # pragma: no cover - placeholder for import
        def __init__(self, parent=None):
            pass

        def __class_getitem__(cls, item):  # type: ignore[override]
            return cls

    base_module.BaseProcessingOperator = BaseProcessingOperator
    sys.modules["processing.base_processing_operator"] = base_module

    path = Path(__file__).resolve().parents[2] / "processing" / "zero_crossing_rate.py"
    spec = importlib.util.spec_from_file_location("processing.zero_crossing_rate", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.ZeroCrossingRate


ZeroCrossingRate = load_zero_crossing_rate()


class DummyAudio:
    def __init__(self, data):
        self._data = data

    def peek(self):
        return self._data


def test_zero_crossing_rate_basic():
    audio = DummyAudio(np.array([1.0, -1.0, 1.0, -1.0]))
    zcr = ZeroCrossingRate(audio)
    assert np.isclose(zcr.process(), 0.75)


def test_zero_crossing_rate_empty():
    audio = DummyAudio(np.array([]))
    zcr = ZeroCrossingRate(audio)
    assert zcr.process() == 0.0
