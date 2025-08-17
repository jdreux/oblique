"""Tests for the transport clock."""

import importlib
from pathlib import Path
import sys
import types
import mido

from tests.utils.stubs import setup_stubs


ROOT = Path(__file__).resolve().parents[1]


def test_basic_progression() -> None:
    setup_stubs()
    sys.modules["inputs"] = types.ModuleType("inputs")
    sys.modules["inputs"].__path__ = [str(ROOT / "inputs")]
    mod = importlib.import_module("inputs.transport.clock")
    TransportClock = mod.TransportClock

    t = 0.0

    def time_source() -> float:
        return t

    clock = TransportClock(bpm=120.0, time_source=time_source)

    state = clock.state()
    assert state.bar == 0
    assert state.beat == 0

    t = 0.5  # one beat at 120 BPM
    state = clock.state()
    assert state.beat == 1

    t = 2.0  # four beats -> next bar
    state = clock.state()
    assert state.bar == 1
    assert state.beat == 0


def test_midi_clock_progression() -> None:
    setup_stubs()
    sys.modules["inputs"] = types.ModuleType("inputs")
    sys.modules["inputs"].__path__ = [str(ROOT / "inputs")]
    mod = importlib.import_module("inputs.transport.clock")
    MidiClock = mod.MidiClock

    t = 0.0

    def time_source() -> float:
        return t

    clock = MidiClock(port=None, time_source=time_source)
    clock._handle(mido.Message("start"))

    tick = 0.5 / clock.TICKS_PER_BEAT
    for _ in range(clock.TICKS_PER_BEAT * 2):
        t += tick
        clock._handle(mido.Message("clock"))

    state = clock.state()
    assert state.bar == 0
    assert state.beat == 2
    assert abs(state.bpm - 120.0) < 1e-6
