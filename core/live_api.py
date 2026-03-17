"""Public API for live-coding patches.

Import these in your patch files instead of relying on builtins::

    from core.live_api import controls, slider, store, midi_learn, midi_map

The functions are no-ops until ``oblique live`` wires them up, so patches
can still be loaded by ``oblique render`` or tests without crashing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from core.param_store import ParamStore

if TYPE_CHECKING:
    from modules.core.base_av_module import BaseAVModule

# -- Module-level state, wired by live.py at startup -------------------------

_controls_fn: Optional[callable] = None
_slider_fn: Optional[callable] = None
_midi_learn_fn: Optional[callable] = None
_midi_map_fn: Optional[callable] = None
_chart_fn: Optional[callable] = None


class _StoreProxy:
    """Proxy so ``from core.live_api import store`` delegates to the real ParamStore."""

    _store: Optional[ParamStore] = None

    def __getattr__(self, name: str):
        if self._store is None:
            raise RuntimeError("store is not available outside of `oblique live`")
        return getattr(self._store, name)


store: ParamStore = _StoreProxy()  # type: ignore[assignment]


def _wire(
    real_store: ParamStore,
    controls_fn: callable,
    slider_fn: callable,
    midi_learn_fn: callable,
    midi_map_fn: callable,
    chart_fn: Optional[callable] = None,
) -> None:
    """Called once by live.py to install the real implementations."""
    global _controls_fn, _slider_fn, _midi_learn_fn, _midi_map_fn, _chart_fn
    store._store = real_store  # type: ignore[attr-defined]
    _controls_fn = controls_fn
    _slider_fn = slider_fn
    _midi_learn_fn = midi_learn_fn
    _midi_map_fn = midi_map_fn
    _chart_fn = chart_fn


# -- Public API ---------------------------------------------------------------


def controls(*modules: "BaseAVModule", group: Optional[str] = None) -> None:
    """Register module params as live-controllable sliders."""
    if _controls_fn is not None:
        _controls_fn(*modules, group=group)


def slider(
    name: str,
    min: float = 0.0,
    max: float = 1.0,
    default: float = 0.5,
    group: str = "custom",
) -> Optional[ParamStore]:
    """Create a standalone slider parameter."""
    if _slider_fn is not None:
        return _slider_fn(name, min=min, max=max, default=default, group=group)
    return None


def midi_learn(param_key: str) -> None:
    """Enter MIDI learn mode for a parameter."""
    if _midi_learn_fn is not None:
        _midi_learn_fn(param_key)


def midi_map(cc: int, param_key: str) -> None:
    """Map a MIDI CC number to a parameter."""
    if _midi_map_fn is not None:
        _midi_map_fn(cc, param_key)


def chart(channel: str, value: float) -> None:
    """Send a data point to a named sparkline chart in the TUI.

    Call this every frame from your tick callback to visualize a value
    over time without flooding the log panel::

        chart("amplitude", amplitude)
    """
    if _chart_fn is not None:
        _chart_fn(channel, value)


def log(*args: object) -> None:
    """Print to the TUI log panel. Drop-in replacement for ``print()``."""
    from core.logger import info
    info(" ".join(str(a) for a in args))
