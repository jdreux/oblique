"""MIDI CC → ParamStore mapping with learn mode.

Polls CC events from a :class:`MidiInput` and writes normalised values into
the :class:`ParamStore`.  The ``learn`` method arms the mapper so that the
next CC received is automatically bound to the given parameter key.
"""

from __future__ import annotations

from typing import Optional

from core.logger import info
from core.param_store import ParamStore


class MidiMapper:
    """Map MIDI CC numbers to ParamStore keys."""

    def __init__(self, store: ParamStore) -> None:
        self._store = store
        self._cc_map: dict[int, str] = {}
        self._learning: Optional[str] = None
        self._midi_input: Optional[object] = None

    def set_input(self, midi_input: object) -> None:
        """Attach a MidiInput (or any object with a ``read()`` method)."""
        self._midi_input = midi_input

    def map(self, cc: int, param_key: str) -> None:
        """Bind a CC number to a ParamStore key."""
        self._cc_map[cc] = param_key
        info(f"MIDI CC {cc} → {param_key}")

    def unmap(self, cc: int) -> None:
        self._cc_map.pop(cc, None)

    def learn(self, param_key: str) -> None:
        """Arm learn mode — next CC received maps to *param_key*."""
        self._learning = param_key
        info(f"MIDI learn armed for {param_key} — move a knob...")

    def poll(self) -> None:
        """Process pending MIDI CC events.  Call once per frame from tick."""
        if self._midi_input is None:
            return
        messages = self._midi_input.read()
        if not messages:
            return
        for msg in messages:
            if not hasattr(msg, "type") or msg.type != "control_change":
                continue
            cc = msg.control
            raw = msg.value  # 0-127

            # Learn mode: bind this CC
            if self._learning is not None:
                self._cc_map[cc] = self._learning
                info(f"MIDI learned: CC {cc} → {self._learning}")
                self._learning = None

            if cc not in self._cc_map:
                continue

            key = self._cc_map[cc]
            if key not in self._store:
                continue

            entry = self._store._entries[key]
            normalized = raw / 127.0
            value = entry.min + normalized * (entry.max - entry.min)
            self._store.set(key, value)

    @property
    def mappings(self) -> dict[int, str]:
        return dict(self._cc_map)
