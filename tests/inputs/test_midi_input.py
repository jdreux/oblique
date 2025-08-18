import sys
from pathlib import Path

from mido import Message

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.modules.pop("inputs", None)

from inputs.midi.core.midi_input import MidiInput


def test_midi_input_handles_messages() -> None:
    midi = MidiInput()
    midi.process_message(Message('note_on', note=60, velocity=100))
    midi.process_message(Message('note_off', note=60, velocity=0))

    # Peek should not clear messages
    peeked = midi.peek()
    assert len(peeked) == 2
    assert peeked[0].type == 'note_on'

    # Read should clear messages
    read_messages = midi.read()
    assert len(read_messages) == 2
    assert midi.read() == []


def test_midi_input_transport_and_bpm() -> None:
    midi = MidiInput()

    midi.process_message(Message('start'))
    assert midi.is_playing is True
    midi.process_message(Message('stop'))
    assert midi.is_playing is False

    # Two MIDI clock messages spaced for 120 BPM (0.5s per beat / 24 clocks)
    midi.process_message(Message('clock'), timestamp=0.0)
    midi.process_message(Message('clock'), timestamp=0.5 / 24)
    assert midi.bpm is not None
    assert abs(midi.bpm - 120.0) < 0.1
