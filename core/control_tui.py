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
from textual.widgets import Footer, Header, Label, RichLog, Sparkline, Static


# -- Custom slider widget -----------------------------------------------------

class ParamBar(Static, can_focus=True):
    """A focusable horizontal slider bar with value overlay."""

    DEFAULT_CSS = """
    ParamBar {
        height: 1;
        min-width: 20;
        background: transparent;
    }
    ParamBar:focus {
        background: transparent;
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

    @staticmethod
    def _fmt(v: float) -> str:
        if abs(v - round(v)) < 0.005 and abs(v) < 100_000:
            return str(int(round(v)))
        if abs(v) >= 100:
            return f"{v:.0f}"
        if abs(v) >= 10:
            return f"{v:.1f}"
        return f"{v:.2f}"

    def render(self) -> str:
        width = max(self.size.width, 1)
        rng = max(self.max_val - self.min_val, 1e-9)
        ratio = max(0.0, min(1.0, (self.value - self.min_val) / rng))
        filled = int(ratio * width)

        val_text = f" {self._fmt(self.value)} "

        bar_f = "\u2588" * filled
        bar_e = "\u2591" * (width - filled)
        bar = list(bar_f + bar_e)

        start = max(0, (width - len(val_text)) // 2)
        for i, ch in enumerate(val_text):
            pos = start + i
            if pos < len(bar):
                bar[pos] = ch

        filled_part = "".join(bar[:filled])
        empty_part = "".join(bar[filled:])

        if self.has_focus:
            return (
                f"[bold white on dodger_blue]{filled_part}[/]"
                f"[bold white on grey27]{empty_part}[/]"
            )
        return (
            f"[white on grey37]{filled_part}[/]"
            f"[grey62 on grey15]{empty_part}[/]"
        )

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

    _dragging: bool = False

    def _set_from_x(self, x: float) -> None:
        width = max(self.size.width, 1)
        ratio = max(0.0, min(1.0, x / width))
        new = self.min_val + ratio * (self.max_val - self.min_val)
        if new != self.value:
            self.value = new
            self.post_message(self.Changed(self, self.value))

    def on_mouse_down(self, event: events.MouseDown) -> None:
        self._dragging = True
        self._set_from_x(event.x)
        self.focus()
        event.stop()

    def on_mouse_move(self, event: events.MouseMove) -> None:
        if self._dragging:
            self._set_from_x(event.x)
            event.stop()

    def on_mouse_up(self, event: events.MouseUp) -> None:
        if self._dragging:
            self._dragging = False
            event.stop()

    def on_click(self, event: events.Click) -> None:
        if not self._dragging:
            self._set_from_x(event.x)
            self.focus()
        event.stop()

    def watch_value(self, new_value: float) -> None:
        self.refresh()

    def on_focus(self) -> None:
        self.refresh()
        self._update_label_style(focused=True)

    def on_blur(self) -> None:
        self.refresh()
        self._update_label_style(focused=False)

    def _update_label_style(self, focused: bool) -> None:
        try:
            row = self.parent
            if row is None:
                return
            for child in row.children:
                if isinstance(child, Label) and (
                    "param-name" in child.classes or "param-name-focused" in child.classes
                ):
                    child.remove_class("param-name", "param-name-focused")
                    child.add_class("param-name-focused" if focused else "param-name")
                    break
        except Exception:
            pass


# -- Telemetry ----------------------------------------------------------------

class TelemetryPanel(Static):
    fps = reactive(0.0)
    frame_time = reactive(0.0)
    frame_count = reactive(0)
    runtime = reactive(0.0)
    memory = reactive("")

    def render(self) -> str:
        return (
            f"  [bold cyan]{self.fps:5.1f}[/] fps"
            f"  [dim]\u2502[/]  [bold]{self.frame_time:5.1f}[/] ms"
            f"  [dim]\u2502[/]  [bold]{self.frame_count}[/] frames"
            f"  [dim]\u2502[/]  [bold]{self.runtime:6.1f}[/] s"
            f"  [dim]\u2502[/]  [bold]{self.memory}[/] MB"
        )


# -- Param row ----------------------------------------------------------------

class ParamSlider(Vertical, can_focus=False):
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
    ParamSlider .param-name-focused {
        width: 22;
        color: $accent;
        text-style: bold;
    }
    ParamSlider .param-range {
        width: 16;
        text-align: right;
        color: $text-muted;
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
        lo = ParamBar._fmt(self.min_val)
        hi = ParamBar._fmt(self.max_val)
        with Horizontal(classes="param-row"):
            yield Label(self.param_name, classes="param-name")
            yield ParamBar(
                min_val=self.min_val,
                max_val=self.max_val,
                value=self.param_value,
                id=f"bar-{safe}",
            )
            yield Label(
                f"[dim]{lo}\u25c2 \u25b8{hi}[/]",
                classes="param-range",
            )


# -- Group header -------------------------------------------------------------

class GroupHeader(Static):
    DEFAULT_CSS = """
    GroupHeader {
        background: $primary-background;
        color: $text;
        padding: 0 1;
        margin: 1 0 0 0;
        text-style: bold;
        border-bottom: solid $primary-background-lighten-2;
    }
    """


# -- Chart panel --------------------------------------------------------------

_CHART_MAX_POINTS = 200


class ChartRow(Horizontal):
    DEFAULT_CSS = """
    ChartRow {
        height: 4;
        margin: 0 1;
    }
    ChartRow .chart-label {
        width: 22;
        color: $text;
    }
    ChartRow .chart-value {
        width: 10;
        text-align: right;
        color: $accent;
    }
    ChartRow Sparkline {
        min-width: 20;
    }
    """

    def __init__(self, channel: str) -> None:
        super().__init__()
        self.channel = channel
        self._data: list[float] = []

    def compose(self) -> ComposeResult:
        yield Label(self.channel, classes="chart-label")
        yield Sparkline(
            data=[0.0],
            min_color="grey37",
            max_color="dodger_blue",
            id=f"spark-{self.channel}",
        )
        yield Label("0.00", classes="chart-value", id=f"chartval-{self.channel}")

    def push(self, value: float) -> None:
        self._data.append(value)
        if len(self._data) > _CHART_MAX_POINTS:
            self._data = self._data[-_CHART_MAX_POINTS:]
        try:
            spark = self.query_one(Sparkline)
            spark.data = list(self._data)
            lbl = self.query_one(f"#chartval-{self.channel}", Label)
            lbl.update(f"[bold]{ParamBar._fmt(value)}[/]")
        except Exception:
            pass


class ChartArea(Vertical):
    DEFAULT_CSS = """
    ChartArea {
        height: auto;
        max-height: 16;
        border-top: solid $primary-background;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._rows: dict[str, ChartRow] = {}
        self._pending: dict[str, float] = {}

    async def _mount_row(self, channel: str) -> None:
        row = ChartRow(channel)
        row.id = f"chartrow-{channel}"
        await self.mount(row)
        self._rows[channel] = row
        # Push any value that arrived while mounting
        if channel in self._pending:
            row.push(self._pending.pop(channel))

    def add_point(self, channel: str, value: float) -> None:
        if not self.is_mounted:
            return
        row = self._rows.get(channel)
        if row is not None:
            row.push(value)
            return
        # Row not created yet — schedule async mount, buffer value
        if channel not in self._pending:
            self.call_later(self._mount_row, channel)
        self._pending[channel] = value


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
    #chart-area {
        dock: bottom;
    }
    """

    BINDINGS: ClassVar = [
        ("q", "quit", "Quit"),
        ("r", "reload", "Reload"),
        ("d", "list_devices", "Devices"),
        ("m", "list_monitors", "Monitors"),
        ("l", "list_modules", "Modules"),
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
        yield ChartArea(id="chart-area")
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
            elif kind == "chart_data" and len(msg) >= 3:
                self._push_chart(msg[1], msg[2])
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
        log_panel.scroll_end(animate=False)

    def _push_chart(self, channel: str, value: float) -> None:
        try:
            area = self.query_one("#chart-area", ChartArea)
            area.add_point(channel, value)
        except Exception:
            pass

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
            f"  [dim]\u2502[/] Shader reload: {shader_icon}"
            f"  [dim]\u2502[/] Python reload: {python_icon}"
        )

    def on_mouse_up(self, event: events.MouseUp) -> None:
        for bar in self.query(ParamBar):
            bar._dragging = False

    def on_param_bar_changed(self, event: ParamBar.Changed) -> None:
        bar_id = event.bar.id or ""
        if bar_id.startswith("bar-"):
            safe_key = bar_id[4:]
            param_key = safe_key.replace("-", ".", 1)
            self._send(("set_param", param_key, event.value))

    def action_reload(self) -> None:
        self._send(("reload",))
        self._append_log("INFO", "Reload requested")

    def action_list_devices(self) -> None:
        self._send(("list_devices",))

    def action_list_monitors(self) -> None:
        self._send(("list_monitors",))

    def action_list_modules(self) -> None:
        self._send(("list_modules",))

    def action_quit(self) -> None:
        self._send(("quit",))
        self.exit()

    def _send(self, msg: tuple) -> None:
        try:
            self._conn.send(msg)
        except (BrokenPipeError, OSError):
            self.exit()
