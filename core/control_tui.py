"""Textual TUI control surface for Oblique live mode.

Runs in a subprocess, communicates with the engine via a
``multiprocessing.Connection`` (pickle-based pipe).
"""

from __future__ import annotations

from multiprocessing.connection import Connection
from typing import Any, ClassVar

from textual import events
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Footer, Header, Label, RichLog, Rule, Static


# -- Custom slider widget -----------------------------------------------------

class ParamBar(Static, can_focus=True):
    """A focusable horizontal slider bar.  Left/Right or click to adjust."""

    DEFAULT_CSS = """
    ParamBar {
        height: 1;
        min-width: 20;
        background: $surface;
    }
    ParamBar:focus {
        background: $surface;
    }
    """

    class Changed(Message):
        def __init__(self, bar: "ParamBar", value: float) -> None:
            super().__init__()
            self.bar = bar
            self.value = value

    value = reactive(0.0)

    def __init__(
        self,
        min_val: float = 0.0,
        max_val: float = 1.0,
        value: float = 0.5,
        step: float = 0.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.min_val = min_val
        self.max_val = max_val
        self.value = value
        self._step = step or (max_val - min_val) / 100

    def render(self) -> str:
        width = max(self.size.width - 2, 1)
        ratio = (self.value - self.min_val) / max(self.max_val - self.min_val, 1e-9)
        ratio = max(0.0, min(1.0, ratio))
        filled = int(ratio * width)
        bar = "\u2588" * filled + "\u2591" * (width - filled)
        if self.has_focus:
            return f"[bold cyan]\u2590{bar}\u258c[/]"
        return f"[dim]\u2590[/][cyan]{bar}[/][dim]\u258c[/]"

    def _nudge(self, direction: int, coarse: bool = False) -> None:
        multiplier = 10 if coarse else 1
        new = self.value + direction * self._step * multiplier
        new = max(self.min_val, min(self.max_val, new))
        if new != self.value:
            self.value = new
            self.post_message(self.Changed(self, self.value))

    def on_key(self, event: events.Key) -> None:
        if event.key == "left":
            self._nudge(-1)
            event.stop()
        elif event.key == "right":
            self._nudge(1)
            event.stop()
        elif event.key == "shift+left":
            self._nudge(-1, coarse=True)
            event.stop()
        elif event.key == "shift+right":
            self._nudge(1, coarse=True)
            event.stop()

    def on_click(self, event: events.Click) -> None:
        width = max(self.size.width - 2, 1)
        ratio = max(0.0, min(1.0, (event.x - 1) / width))
        self.value = self.min_val + ratio * (self.max_val - self.min_val)
        self.post_message(self.Changed(self, self.value))
        self.focus()

    def watch_value(self, new_value: float) -> None:
        self.refresh()


# -- Telemetry ----------------------------------------------------------------

class TelemetryPanel(Static):
    fps = reactive(0.0)
    frame_time = reactive(0.0)
    frame_count = reactive(0)
    runtime = reactive(0.0)
    memory = reactive("")

    def render(self) -> str:
        return (
            f"  FPS [bold cyan]{self.fps:5.1f}[/]"
            f"  \u250a  Frame [bold]{self.frame_time:5.1f}[/] ms"
            f"  \u250a  Frames [bold]{self.frame_count}[/]"
            f"  \u250a  Runtime [bold]{self.runtime:6.1f}[/] s"
            f"  \u250a  Mem [bold]{self.memory}[/]"
        )


# -- Param row ----------------------------------------------------------------

class ParamSlider(Vertical):
    DEFAULT_CSS = """
    ParamSlider {
        height: auto;
        margin: 0 1;
        padding: 0;
    }
    ParamSlider .param-row {
        height: 1;
    }
    ParamSlider .param-name {
        width: 22;
        color: $text;
    }
    ParamSlider .param-value {
        width: 10;
        text-align: right;
        color: $accent;
    }
    ParamSlider .param-desc {
        color: $text-muted;
        margin: 0 0 0 2;
    }
    """

    def __init__(
        self,
        param_key: str,
        name: str,
        value: float,
        min_val: float,
        max_val: float,
        description: str = "",
    ) -> None:
        super().__init__()
        self.param_key = param_key
        self.param_name = name
        self.param_value = value
        self.min_val = min_val
        self.max_val = max_val
        self.description = description

    @staticmethod
    def _safe_id(key: str) -> str:
        return key.replace(".", "-")

    def compose(self) -> ComposeResult:
        safe = self._safe_id(self.param_key)
        with Horizontal(classes="param-row"):
            yield Label(self.param_name, classes="param-name")
            yield ParamBar(
                min_val=self.min_val,
                max_val=self.max_val,
                value=self.param_value,
                id=f"bar-{safe}",
            )
            yield Label(
                f"{self.param_value:.2f}",
                classes="param-value",
                id=f"val-{safe}",
            )
        if self.description:
            yield Label(f"  {self.description}", classes="param-desc")


# -- Group header -------------------------------------------------------------

class GroupHeader(Static):
    DEFAULT_CSS = """
    GroupHeader {
        background: $primary-background;
        color: $text;
        padding: 0 1;
        margin: 1 0 0 0;
        text-style: bold;
    }
    """


# -- Log panel ----------------------------------------------------------------

class LogPanel(RichLog):
    DEFAULT_CSS = """
    LogPanel {
        height: 8;
        border-top: solid $primary-background;
        background: $surface;
        scrollbar-size: 1 1;
    }
    """


# -- App ----------------------------------------------------------------------

class ControlTUI(App):
    TITLE = "Oblique Controls"

    CSS = """
    Screen {
        background: $surface;
    }
    TelemetryPanel {
        dock: top;
        height: 1;
        background: $primary-background;
        color: $text;
        padding: 0 1;
    }
    #slider-area {
        margin: 0 1;
    }
    #status-bar {
        dock: bottom;
        height: 1;
        background: $primary-background;
        color: $text-muted;
        padding: 0 1;
    }
    LogPanel {
        dock: bottom;
    }
    """

    BINDINGS: ClassVar = [
        ("q", "quit", "Quit"),
        ("r", "reload", "Reload"),
        ("tab", "focus_next", "Next"),
        ("shift+tab", "focus_previous", "Prev"),
    ]

    def __init__(self, conn: Connection) -> None:
        super().__init__()
        self._conn = conn
        self._params: dict[str, dict[str, Any]] = {}
        self._status: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        yield TelemetryPanel()
        yield VerticalScroll(id="slider-area")
        yield LogPanel(id="log-panel", max_lines=200)
        yield Static("", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(0.05, self._poll_ipc)

    def _poll_ipc(self) -> None:
        """Drain all pending messages from the engine."""
        drained = 0
        while drained < 50:
            if not self._conn.poll(0):
                break
            try:
                msg = self._conn.recv()
            except (EOFError, OSError):
                self.exit()
                return
            drained += 1
            if not isinstance(msg, tuple) or len(msg) == 0:
                continue
            kind = msg[0]
            if kind == "telemetry" and len(msg) >= 2:
                self._apply_telemetry(msg[1])
            elif kind == "params_snapshot" and len(msg) >= 2:
                self._rebuild_sliders(msg[1])
            elif kind == "param_update" and len(msg) >= 3:
                self._update_single_slider(msg[1], msg[2])
            elif kind == "log" and len(msg) >= 3:
                self._append_log(msg[1], msg[2])
            elif kind == "status" and len(msg) >= 2:
                self._apply_status(msg[1])

    def _apply_telemetry(self, stats: dict[str, Any]) -> None:
        try:
            panel = self.query_one(TelemetryPanel)
        except Exception:
            return
        panel.fps = stats.get("avg_fps", stats.get("fps", 0.0))
        panel.frame_time = stats.get("frame_time_ms", 0.0)
        panel.frame_count = stats.get("frame_count", 0)
        panel.runtime = stats.get("runtime", 0.0)
        panel.memory = str(stats.get("memory", ""))

    def _rebuild_sliders(self, snapshot: dict[str, dict[str, Any]]) -> None:
        self._params = snapshot
        try:
            area = self.query_one("#slider-area", VerticalScroll)
        except Exception:
            return
        area.remove_children()

        groups: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        for key, info in snapshot.items():
            g = info.get("group", "default")
            groups.setdefault(g, []).append((key, info))

        for group_name, entries in groups.items():
            area.mount(GroupHeader(f"\u25b8 {group_name}"))
            area.mount(Rule(line_style="dashed"))
            for key, info in entries:
                area.mount(
                    ParamSlider(
                        param_key=key,
                        name=info["name"],
                        value=info["value"],
                        min_val=info["min"],
                        max_val=info["max"],
                        description=info.get("description", ""),
                    )
                )

    def _update_single_slider(self, key: str, value: float) -> None:
        safe = ParamSlider._safe_id(key)
        try:
            bar = self.query_one(f"#bar-{safe}", ParamBar)
            bar.value = value
            val_label = self.query_one(f"#val-{safe}", Label)
            val_label.update(f"{value:.2f}")
        except Exception:
            pass

    def _append_log(self, level: str, message: str) -> None:
        try:
            log_panel = self.query_one("#log-panel", LogPanel)
        except Exception:
            return
        if level in ("ERROR", "FATAL"):
            log_panel.write(f"[bold red]{level}[/] {message}")
        elif level == "WARNING":
            log_panel.write(f"[yellow]{level}[/] {message}")
        else:
            log_panel.write(f"[dim]{level}[/] {message}")

    def _apply_status(self, info: dict[str, Any]) -> None:
        self._status = info
        try:
            bar = self.query_one("#status-bar", Static)
        except Exception:
            return
        patch = info.get("patch", "?")
        shader_icon = "\u2713" if info.get("shaders") else "\u2717"
        python_icon = "\u2713" if info.get("python") else "\u2717"
        bar.update(
            f"  Patch: [bold]{patch}[/]"
            f"  | Shader reload: {shader_icon}"
            f"  | Python reload: {python_icon}"
        )

    def on_param_bar_changed(self, event: ParamBar.Changed) -> None:
        bar_id = event.bar.id or ""
        if bar_id.startswith("bar-"):
            safe_key = bar_id[4:]
            try:
                val_label = self.query_one(f"#val-{safe_key}", Label)
                val_label.update(f"{event.value:.2f}")
            except Exception:
                pass
            # Reverse the safe_id to get the param key
            param_key = safe_key.replace("-", ".", 1)
            self._send(("set_param", param_key, event.value))

    def action_reload(self) -> None:
        self._send(("reload",))
        self._append_log("INFO", "Reload requested")

    def action_quit(self) -> None:
        self._send(("quit",))
        self.exit()

    def _send(self, msg: tuple) -> None:
        try:
            self._conn.send(msg)
        except (BrokenPipeError, OSError):
            self.exit()
