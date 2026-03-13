import json
from pathlib import Path

from core.param_store import ParamStore


def test_register_and_get():
    store = ParamStore()
    store.register(name="speed", group="cube", default=1.0, min=0.0, max=5.0)
    assert store.get("cube.speed") == 1.0


def test_set_clamps():
    store = ParamStore()
    store.register(name="amp", group="g", default=0.5, min=0.0, max=1.0)
    store.set("g.amp", 2.0)
    assert store.get("g.amp") == 1.0
    store.set("g.amp", -1.0)
    assert store.get("g.amp") == 0.0


def test_bind_returns_callable():
    store = ParamStore()
    store.register(name="x", group="g", default=0.3, min=0.0, max=1.0)
    fn = store.bind("g.x")
    assert fn() == 0.3
    store.set("g.x", 0.7)
    assert fn() == 0.7


def test_groups_and_entries():
    store = ParamStore()
    store.register(name="a", group="g1", default=0.0, min=0.0, max=1.0)
    store.register(name="b", group="g2", default=0.0, min=0.0, max=1.0)
    assert set(store.groups()) == {"g1", "g2"}
    assert len(store.entries_for_group("g1")) == 1


def test_on_change_callback():
    store = ParamStore()
    store.register(name="x", group="g", default=0.5, min=0.0, max=1.0)
    changes: list[tuple[str, float]] = []
    store._on_change = lambda key, val: changes.append((key, val))

    store.set("g.x", 0.8)
    assert changes == [("g.x", 0.8)]

    # Clamped value should be reported
    store.set("g.x", 2.0)
    assert changes[-1] == ("g.x", 1.0)


def test_on_change_not_called_for_missing_key():
    store = ParamStore()
    store.register(name="x", group="g", default=0.5, min=0.0, max=1.0)
    changes: list[tuple[str, float]] = []
    store._on_change = lambda key, val: changes.append((key, val))

    store.set("nonexistent.key", 0.5)
    assert changes == []


def test_save_load(tmp_path: Path):
    store = ParamStore()
    store.register(name="x", group="g", default=0.5, min=0.0, max=1.0)
    store.set("g.x", 0.8)

    preset = tmp_path / "preset.json"
    store.save(preset)

    store2 = ParamStore()
    store2.register(name="x", group="g", default=0.5, min=0.0, max=1.0)
    store2.load(preset)
    assert store2.get("g.x") == 0.8
