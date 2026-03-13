"""REPL helper functions for live performance.

These are injected into the REPL namespace so the performer can type
``controls(cube)`` or ``midi_learn("Tesseract.speed")`` interactively.
"""

from __future__ import annotations

from dataclasses import fields
from typing import TYPE_CHECKING, Any, Optional

from core.logger import info as _log_info
from core.param_store import ParamStore

if TYPE_CHECKING:
    from core.midi_mapper import MidiMapper
    from modules.core.base_av_module import BaseAVModule


def register_module_params(
    module: "BaseAVModule",
    store: ParamStore,
    group: Optional[str] = None,
) -> None:
    """Introspect a module's Params dataclass and register controllable fields."""
    params = module.params
    group_name = group or module.__class__.__name__

    for f in fields(params):
        if f.name in ("width", "height"):
            continue
        meta = f.metadata
        if "min" not in meta or "max" not in meta:
            continue
        key = f"{group_name}.{f.name}"
        if key in store:
            continue

        current = getattr(params, f.name)
        default = float(current) if isinstance(current, (int, float)) else float(f.default)

        store.register(
            name=f.name,
            group=group_name,
            default=default,
            min=float(meta["min"]),
            max=float(meta["max"]),
            description=meta.get("description", ""),
        )
        # Wire the param to read from the store.
        # Wrap int fields so the callable returns int (shaders need correct types).
        bound = store.bind(key)
        is_int = isinstance(current, int) and not isinstance(current, bool)
        if is_int:
            setattr(params, f.name, lambda _b=bound: int(_b()))
        else:
            setattr(params, f.name, bound)


def make_controls_fn(
    store: ParamStore,
    control_window: Optional[Any],
) -> callable:
    """Build the ``controls(module, group=...)`` helper for the REPL."""

    def controls(*modules: "BaseAVModule", group: Optional[str] = None) -> None:
        for mod in modules:
            g = group if len(modules) == 1 else None
            register_module_params(mod, store, group=g or None)
        if control_window is not None:
            control_window.mark_dirty()
        count = sum(1 for _ in store.all_entries())
        _log_info(f"[controls] {count} params registered — sliders updated")

    return controls


def make_slider_fn(
    store: ParamStore,
    control_window: Optional[Any],
) -> callable:
    """Build the ``slider(name, min, max, default, group)`` helper."""

    def slider(
        name: str,
        min: float = 0.0,
        max: float = 1.0,
        default: float = 0.5,
        group: str = "custom",
    ) -> "ParamStore":
        store.register(name=name, group=group, default=default, min=min, max=max)
        if control_window is not None:
            control_window.mark_dirty()
        key = f"{group}.{name}"
        _log_info(f"[slider] {key} created — use store.bind('{key}') to wire it")
        return store

    return slider


def make_midi_learn_fn(mapper: "MidiMapper") -> callable:
    def midi_learn(param_key: str) -> None:
        mapper.learn(param_key)

    return midi_learn


def make_midi_map_fn(mapper: "MidiMapper") -> callable:
    def midi_map(cc: int, param_key: str) -> None:
        mapper.map(cc, param_key)

    return midi_map


def make_set_scene_fn(engine_ref: list) -> callable:
    """Build ``set_scene(module)`` — hot-swaps the active scene."""

    def set_scene(module: "BaseAVModule") -> None:
        engine = engine_ref[0]
        # Replace the tick callback with one that always returns this module
        original_patch = engine.patch
        original_patch._override_scene = module
        print("[set_scene] Scene swapped — next frame will render the new module")

    return set_scene
