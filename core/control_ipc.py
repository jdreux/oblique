"""Engine-side IPC bridge for communicating with the TUI subprocess.

Sends telemetry, param snapshots, and log messages over a
``multiprocessing.Connection``.  Receives ``set_param``, ``reload``,
and ``quit`` commands from the TUI.

Outbound messages are queued and sent from a background thread so the
render loop is never blocked by a full pipe buffer or a dead subprocess.
"""

from __future__ import annotations

import queue
import threading
import time
from multiprocessing.connection import Connection
from typing import Any, Optional

from core.param_store import ParamStore

_SEND_QUEUE_MAX = 64  # drop oldest if the TUI can't keep up


class ControlBridge:
    """Bidirectional bridge between the engine (main process) and TUI subprocess."""

    def __init__(self, conn: Connection, store: ParamStore) -> None:
        self._conn = conn
        self._store = store
        self._last_telemetry = 0.0
        self._last_chart: dict[str, float] = {}
        self._closed = False

        # Background sender — keeps the render loop non-blocking
        self._queue: queue.Queue[tuple] = queue.Queue(maxsize=_SEND_QUEUE_MAX)
        self._sender_stop = threading.Event()
        self._sender_thread = threading.Thread(
            target=self._sender_loop, daemon=True
        )
        self._sender_thread.start()

    # -- Outbound -------------------------------------------------------------

    def send_telemetry(self, stats: dict[str, Any]) -> None:
        """Send telemetry dict to TUI, throttled to ~10 Hz."""
        now = time.monotonic()
        if now - self._last_telemetry < 0.1:
            return
        self._last_telemetry = now
        self._enqueue(("telemetry", stats))

    def send_params_snapshot(self) -> None:
        """Send full param state to TUI for slider rebuilding."""
        snapshot: dict[str, dict[str, Any]] = {}
        for entry in self._store.all_entries():
            key = f"{entry.group}.{entry.name}"
            snapshot[key] = {
                "value": entry.value,
                "min": entry.min,
                "max": entry.max,
                "name": entry.name,
                "group": entry.group,
                "description": entry.description,
            }
        self._enqueue(("params_snapshot", snapshot), priority=True)

    def send_param_update(self, key: str, value: float) -> None:
        """Forward a single param change (e.g. from MIDI) to TUI."""
        self._enqueue(("param_update", key, value))

    def send_chart_data(self, channel: str, value: float) -> None:
        """Send a data point to a named chart channel in the TUI (~20 Hz)."""
        now = time.monotonic()
        if now - self._last_chart.get(channel, 0.0) < 0.05:
            return
        self._last_chart[channel] = now
        self._enqueue(("chart_data", channel, value))

    def send_log(self, level: str, message: str) -> None:
        """Send a log line to the TUI log panel."""
        self._enqueue(("log", level, message), priority=True)

    def send_status(self, info: dict[str, Any]) -> None:
        """Send status metadata (patch name, hot-reload flags, etc.)."""
        self._enqueue(("status", info), priority=True)

    def mark_dirty(self) -> None:
        """Duck-type compatible with old ControlWindow.mark_dirty()."""
        self.send_params_snapshot()

    # -- Inbound --------------------------------------------------------------

    def poll_incoming(self) -> Optional[str]:
        """Drain all pending TUI messages.

        Applies ``set_param`` immediately.  Returns ``"quit"`` or
        ``"reload"`` if the TUI requested it, otherwise ``None``.
        """
        if self._closed:
            return "quit"
        result: Optional[str] = None
        try:
            while self._conn.poll(0):
                try:
                    msg = self._conn.recv()
                except (EOFError, OSError):
                    self._closed = True
                    return "quit"
                if not isinstance(msg, tuple) or len(msg) == 0:
                    continue
                kind = msg[0]
                if kind == "set_param" and len(msg) >= 3:
                    # Suppress _on_change to avoid feedback loop back to TUI
                    saved = self._store._on_change
                    self._store._on_change = None
                    self._store.set(msg[1], msg[2])
                    self._store._on_change = saved
                elif kind == "reload":
                    result = "reload"
                elif kind == "quit":
                    result = "quit"
                elif kind == "list_devices":
                    self._run_list_command("devices")
                elif kind == "list_monitors":
                    self._run_list_command("monitors")
                elif kind == "list_modules":
                    self._run_list_command("modules")
        except (EOFError, OSError):
            self._closed = True
            return "quit"
        return result

    # -- Lifecycle ------------------------------------------------------------

    def close(self) -> None:
        """Close the connection and stop the sender thread."""
        if not self._closed:
            self._closed = True
            self._sender_stop.set()
            try:
                self._conn.close()
            except OSError:
                pass
            self._sender_thread.join(timeout=1.0)

    def _run_list_command(self, kind: str) -> None:
        """Run a list-* command and send the output as log messages."""
        import io

        buf = io.StringIO()
        try:
            if kind == "devices":
                import sounddevice as sd
                all_devs = sd.query_devices()
                buf.write("Audio Devices:\n")
                for i, dev in enumerate(all_devs):
                    direction = ""
                    if dev["max_input_channels"] > 0:
                        direction += "IN"
                    if dev["max_output_channels"] > 0:
                        direction += "/OUT" if direction else "OUT"
                    buf.write(
                        f"  [{i}] {dev['name']}  "
                        f"({direction}, {int(dev['default_samplerate'])} Hz)\n"
                    )
            elif kind == "monitors":
                import glfw
                monitors = glfw.get_monitors()
                buf.write("Monitors:\n")
                for i, mon in enumerate(monitors):
                    name = glfw.get_monitor_name(mon)
                    mode = glfw.get_video_mode(mon)
                    w, h = mode.size.width, mode.size.height
                    buf.write(f"  [{i}] {name}  ({w}x{h} @ {mode.refresh_rate}Hz)\n")
            elif kind == "modules":
                from core.registry import discover_modules, search_modules
                discover_modules()
                specs = search_modules()
                buf.write("Modules:\n")
                for spec in specs:
                    buf.write(
                        f"  {spec.name}  "
                        f"[{spec.category}]  {spec.description}\n"
                    )
        except Exception as e:
            buf.write(f"Error: {e}\n")

        for line in buf.getvalue().rstrip().split("\n"):
            self.send_log("INFO", line)

    # -- Internal -------------------------------------------------------------

    def _enqueue(self, msg: tuple, priority: bool = False) -> None:
        """Put a message on the send queue, dropping oldest if full.

        When *priority* is True the message is never dropped — instead
        we evict as many old messages as needed to make room.
        """
        if self._closed:
            return
        try:
            self._queue.put_nowait(msg)
        except queue.Full:
            if not priority:
                return  # expendable message (e.g. telemetry) — just drop it
            # Make room for priority messages by evicting old entries
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._queue.put_nowait(msg)
            except queue.Full:
                pass

    def _sender_loop(self) -> None:
        """Background thread that drains the queue and writes to the pipe."""
        while not self._sender_stop.is_set():
            try:
                msg = self._queue.get(timeout=0.05)
            except queue.Empty:
                continue
            if self._closed:
                break
            try:
                self._conn.send(msg)
            except (BrokenPipeError, OSError):
                self._closed = True
                break
