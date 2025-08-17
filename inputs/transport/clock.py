"""Transport clocks with Link and MIDI synchronization."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Protocol

import abletonlink  # type: ignore
import mido  # type: ignore


@dataclass
class ClockState:
    """Current timing information."""

    bpm: float
    beat: int
    phase: float
    bar: int
    beats_per_bar: int


class Transport(Protocol):
    """Interface implemented by all transport clocks."""

    def state(self) -> ClockState:
        """Return the current :class:`ClockState`."""


class TransportClock(Transport):
    """Internal clock tracking tempo and musical position."""

    def __init__(
        self,
        bpm: float = 120.0,
        beats_per_bar: int = 4,
        time_source: Callable[[], float] | None = None,
    ) -> None:
        self._bpm = bpm
        self.beats_per_bar = beats_per_bar
        self._time = time_source or time.monotonic
        self._start_time = self._time()

    @property
    def bpm(self) -> float:
        """Return current tempo in beats per minute."""

        return self._bpm

    def set_bpm(self, bpm: float) -> None:
        """Update tempo while keeping phase continuous."""

        state = self.state()
        self._bpm = bpm
        beats_elapsed = state.bar * self.beats_per_bar + state.beat + state.phase
        self._start_time = self._time() - beats_elapsed * 60.0 / bpm

    def state(self) -> ClockState:
        """Return the current :class:`ClockState`."""

        elapsed = self._time() - self._start_time
        total_beats = elapsed * self._bpm / 60.0
        bar = int(total_beats // self.beats_per_bar)
        beat = int(total_beats % self.beats_per_bar)
        phase = total_beats % 1.0
        return ClockState(self._bpm, beat, phase, bar, self.beats_per_bar)


class AbletonLinkClock(TransportClock):
    """Clock synchronized via Ableton Link.

    Tempo changes are propagated to the Link session so multiple peers stay in
    phase.
    """

    def __init__(
        self,
        bpm: float = 120.0,
        beats_per_bar: int = 4,
        time_source: Callable[[], float] | None = None,
    ) -> None:
        super().__init__(bpm, beats_per_bar, time_source)
        self._link = abletonlink.Link(bpm)  # pragma: no cover - requires external lib
        self._session = self._link.capture_session_state()
        self._link.enable(True)

    def set_bpm(self, bpm: float) -> None:  # pragma: no cover - requires Link
        super().set_bpm(bpm)
        self._session.set_tempo(bpm, self._link.clock().micros())
        self._link.commit_session_state(self._session)

    def state(self) -> ClockState:
        self._session = self._link.capture_session_state()  # pragma: no cover - requires Link
        beat_time = self._session.beat()
        tempo = self._session.tempo()
        bar = int(beat_time // self.beats_per_bar)
        beat = int(beat_time % self.beats_per_bar)
        phase = beat_time % 1.0
        self._bpm = tempo
        return ClockState(tempo, beat, phase, bar, self.beats_per_bar)


class MidiClock(TransportClock):
    """Clock synchronized to incoming MIDI clock messages.

    The class listens for MIDI realtime messages (start/stop/clock) and updates
    the internal transport so external devices like Elektron machines stay in
    phase.
    """

    TICKS_PER_BEAT = 24

    def __init__(
        self,
        port: str | None = None,
        bpm: float = 120.0,
        beats_per_bar: int = 4,
        time_source: Callable[[], float] | None = None,
    ) -> None:
        super().__init__(bpm, beats_per_bar, time_source)
        self._tick_count = 0
        self._running = False
        self._last_tick: float | None = None
        self._midi_in = None
        if port is not None:  # pragma: no cover - requires MIDI
            self._midi_in = mido.open_input(port, callback=self._handle)

    def _handle(self, msg) -> None:  # pragma: no cover - callback
        """Process a MIDI message."""

        if msg.type == "start":
            self._running = True
            self._tick_count = 0
            self._last_tick = None
            self._start_time = self._time()
        elif msg.type == "stop":
            self._running = False
        elif msg.type == "clock" and self._running:
            now = self._time()
            if self._last_tick is not None:
                delta = now - self._last_tick
                if delta > 0:
                    bpm = 60.0 / (delta * self.TICKS_PER_BEAT)
                    super().set_bpm(bpm)
            self._tick_count += 1
            beats_elapsed = self._tick_count / self.TICKS_PER_BEAT
            self._start_time = now - beats_elapsed * 60.0 / self._bpm
            self._last_tick = now

    def close(self) -> None:  # pragma: no cover - requires MIDI
        """Close the underlying MIDI port if open."""

        if self._midi_in is not None:
            self._midi_in.close()
