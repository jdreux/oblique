import time
from collections import deque
from typing import Deque, List, Optional

import mido
from mido import Message

from core.logger import info
from inputs.base_input import BaseInput


class MidiInput(BaseInput):
    """Real-time MIDI input using :mod:`mido`.

    The class listens for all MIDI messages, including note events, control changes
    and transport messages such as clock and start/stop. MIDI clock messages are
    used to estimate the tempo (``bpm``).
    """

    def __init__(self, port_name: Optional[str] = None) -> None:
        """Create a MIDI input.

        Parameters
        ----------
        port_name:
            Optional name of the MIDI input port. If ``None`` the default port is
            used when :meth:`start` is called.
        """
        self.port_name = port_name
        self._port: Optional[mido.ports.BaseInput] = None
        self._queue: Deque[Message] = deque()
        self._last_clock_time: Optional[float] = None
        self.bpm: Optional[float] = None
        self.is_playing = False

    @property
    def device_name(self) -> str:
        """Return the name of the MIDI device if available."""
        if self._port is not None:
            return getattr(self._port, "name", self.port_name or "Unknown")
        return self.port_name or "Unknown"

    def start(self) -> None:
        """Open the MIDI input port."""
        if self._port is None:
            self._port = mido.open_input(name=self.port_name)

    def stop(self) -> None:
        """Close the MIDI input port."""
        if self._port is not None:
            self._port.close()
            self._port = None

    def process_message(self, message: Message, timestamp: Optional[float] = None) -> None:
        """Handle an incoming MIDI message.

        Parameters
        ----------
        message:
            Incoming :class:`mido.Message` instance.
        timestamp:
            Optional timestamp in seconds. Defaults to ``time.time()``.
        """
        if timestamp is None:
            timestamp = time.time()

        if message.type == "clock":
            if self._last_clock_time is not None:
                delta = timestamp - self._last_clock_time
                if delta > 0:
                    self.bpm = 60.0 / (delta * 24)
            self._last_clock_time = timestamp
        elif message.type == "start":
            self.is_playing = True
        elif message.type == "stop":
            self.is_playing = False

        self._queue.append(message)

    def _poll(self) -> None:
        """Poll the underlying port for new messages."""
        if self._port is None:
            return
        for msg in self._port.iter_pending():
            self.process_message(msg)

    def read(self) -> List[Message]:
        """Return and clear queued MIDI messages."""
        self._poll()
        messages = list(self._queue)
        self._queue.clear()
        return messages

    def peek(self) -> List[Message]:
        """Return queued MIDI messages without clearing them."""
        self._poll()
        return list(self._queue)


def list_midi_input_ports() -> List[str]:
    """List available MIDI input port names."""
    return mido.get_input_names()


def print_midi_input_ports() -> None:
    """Log the available MIDI input ports."""
    for name in list_midi_input_ports():
        info(name)


if __name__ == "__main__":
    info("Available MIDI inputs:")
    print_midi_input_ports()
