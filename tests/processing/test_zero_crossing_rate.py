import importlib.util
import sys
import types
from pathlib import Path
from typing import Any, Type

import numpy as np


def load_zero_crossing_rate() -> Type[Any]:
    # Create mock modules to satisfy imports - need proper nested structure

    # Create inputs package
    inputs_pkg = types.ModuleType("inputs")
    sys.modules["inputs"] = inputs_pkg

    # Create inputs.audio package
    audio_pkg = types.ModuleType("inputs.audio")
    sys.modules["inputs.audio"] = audio_pkg
    setattr(inputs_pkg, "audio", audio_pkg)

    # Create inputs.audio.core package
    core_pkg = types.ModuleType("inputs.audio.core")
    sys.modules["inputs.audio.core"] = core_pkg
    setattr(audio_pkg, "core", core_pkg)

    # Create inputs.audio.core.audio_device_input module
    audio_device_input_module = types.ModuleType("inputs.audio.core.audio_device_input")
    sys.modules["inputs.audio.core.audio_device_input"] = audio_device_input_module
    setattr(core_pkg, "audio_device_input", audio_device_input_module)

    class AudioDeviceInput:  # pragma: no cover - placeholder for import
        pass

    setattr(audio_device_input_module, "AudioDeviceInput", AudioDeviceInput)

    # Create processing package and base operator
    processing_pkg = types.ModuleType("processing")
    sys.modules["processing"] = processing_pkg

    base_module = types.ModuleType("processing.base_processing_operator")
    sys.modules["processing.base_processing_operator"] = base_module
    setattr(processing_pkg, "base_processing_operator", base_module)

    class BaseProcessingOperator:  # pragma: no cover - placeholder for import
        def __init__(self, parent: Any = None) -> None:
            pass

        def __class_getitem__(cls, item: Any) -> Type["BaseProcessingOperator"]:
            return cls

    setattr(base_module, "BaseProcessingOperator", BaseProcessingOperator)

    # Load the actual module
    path = Path(__file__).resolve().parents[2] / "processing" / "zero_crossing_rate.py"
    spec = importlib.util.spec_from_file_location("processing.zero_crossing_rate", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ZeroCrossingRate


ZeroCrossingRate = load_zero_crossing_rate()


class DummyAudio:
    def __init__(self, data: np.ndarray) -> None:
        self._data = data

    def peek(self) -> np.ndarray:
        return self._data


def test_zero_crossing_rate_basic() -> None:
    audio = DummyAudio(np.array([1.0, -1.0, 1.0, -1.0]))
    zcr = ZeroCrossingRate(audio)
    assert np.isclose(zcr.process(), 0.75)


def test_zero_crossing_rate_empty() -> None:
    audio = DummyAudio(np.array([]))
    zcr = ZeroCrossingRate(audio)
    assert zcr.process() == 0.0


def test_zero_crossing_rate_none_and_stereo() -> None:
    audio_none = DummyAudio(None)
    zcr = ZeroCrossingRate(audio_none)
    assert zcr.process() == 0.0

    stereo = np.array([[1.0, 1.0], [-1.0, -1.0], [1.0, 1.0], [-1.0, -1.0]])
    zcr = ZeroCrossingRate(DummyAudio(stereo))
    assert np.isclose(zcr.process(), 0.75)
