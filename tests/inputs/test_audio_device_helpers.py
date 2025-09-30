"""Tests for high-level audio device helper utilities."""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

import pytest


def _reload_audio_module() -> types.ModuleType:
    """Load the real audio_device_input module, clearing any stubs first."""

    root = Path(__file__).resolve().parents[2]
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)

    for name in list(sys.modules):
        if name == "inputs" or name.startswith("inputs."):
            del sys.modules[name]

    return importlib.import_module("inputs.audio.core.audio_device_input")


@pytest.fixture
def audio_module():
    return _reload_audio_module()


@pytest.fixture
def fake_sounddevice(monkeypatch, audio_module):
    """Stub out sounddevice APIs to provide deterministic devices."""

    devices = [
        {"name": "Built-in Output", "max_input_channels": 0, "hostapi": 0, "default_samplerate": 44100},
        {"name": "Scarlett 2i2", "max_input_channels": 2, "hostapi": 0, "default_samplerate": 48000},
        {"name": "MegaSynth", "max_input_channels": 8, "hostapi": 0, "default_samplerate": 96000},
    ]
    hostapis = [{"name": "CoreAudio"}]

    monkeypatch.setattr(
        audio_module,
        "sd",
        types.SimpleNamespace(
            query_devices=lambda: devices,
            query_hostapis=lambda: hostapis,
        ),
    )

    return audio_module


def test_iter_audio_devices_skips_outputs(fake_sounddevice):
    descriptors = list(fake_sounddevice.iter_audio_devices())
    assert [d.name for d in descriptors] == ["Scarlett 2i2", "MegaSynth"]
    assert descriptors[0].backend == "CoreAudio"


def test_find_audio_device_like_prefers_capable_device(fake_sounddevice):
    descriptor = fake_sounddevice.find_audio_device_like("synth")
    assert descriptor is not None
    assert descriptor.name == "MegaSynth"
    assert descriptor.max_input_channels == 8


def test_audio_device_like_creates_input(monkeypatch, fake_sounddevice):
    created: dict[str, object] = {}

    class DummyInput:
        def __init__(self, *, device_id, channels=None, samplerate=None, chunk_size=None):
            created.update(
                {
                    "device_id": device_id,
                    "channels": channels,
                    "samplerate": samplerate,
                    "chunk_size": chunk_size,
                }
            )

    monkeypatch.setattr(fake_sounddevice, "AudioDeviceInput", DummyInput)

    instance = fake_sounddevice.audio_device_like("scarlett", channels=[0, 1], chunk_size=512)
    assert isinstance(instance, DummyInput)
    assert created["device_id"] == 1
    assert created["channels"] == [0, 1]
    assert created["chunk_size"] == 512
    assert created["samplerate"] == 48000


def test_audio_device_like_raises_on_no_match(fake_sounddevice):
    with pytest.raises(RuntimeError):
        fake_sounddevice.audio_device_like("does-not-exist")


def test_find_audio_device_like_validates_regex(fake_sounddevice):
    with pytest.raises(ValueError):
        fake_sounddevice.find_audio_device_like("[unclosed")
