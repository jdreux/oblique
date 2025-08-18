import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

import numpy as np
import numpy as np
import pytest
from pathlib import Path
from tests.utils.stubs import setup_stubs, load_module


ROOT = Path(__file__).resolve().parents[2]


def _create_engine():
    setup_stubs()
    patch_mod = load_module("core.oblique_patch", ROOT / "core" / "oblique_patch.py")
    engine_mod = load_module("core.oblique_engine", ROOT / "core" / "oblique_engine.py")
    patch = patch_mod.ObliquePatch(lambda t: None)
    return engine_mod.ObliqueEngine(patch, hot_reload_shaders=True)


def test_get_performance_stats():
    engine = _create_engine()
    pm = engine.performance_monitor
    pm.begin_frame()
    pm.end_frame()
    stats = engine.get_performance_stats()
    assert stats is not None
    assert "avg_fps" in stats


def test_render_patch_requires_context():
    setup_stubs()
    patch_mod = load_module("core.oblique_patch", ROOT / "core" / "oblique_patch.py")
    engine_mod = load_module("core.oblique_engine", ROOT / "core" / "oblique_engine.py")
    patch = patch_mod.ObliquePatch(lambda t: None)
    engine = engine_mod.ObliqueEngine(patch)
    with pytest.raises(RuntimeError):
        engine._render_patch(0.0, patch)


def test_display_frame_requires_resources():
    engine = _create_engine()
    with pytest.raises(RuntimeError):
        engine._display_frame(object(), 0.0)


def test_audio_stream_playback(monkeypatch):
    setup_stubs()
    patch_mod = load_module("core.oblique_patch", ROOT / "core" / "oblique_patch.py")
    engine_mod = load_module("core.oblique_engine", ROOT / "core" / "oblique_engine.py")
    import sounddevice as sd

    writes = []

    class DummyOutputStream:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            pass

        def write(self, chunk):
            writes.append(chunk)

    monkeypatch.setattr(sd, "OutputStream", DummyOutputStream)

    class DummyInput:
        sample_rate = 48000
        num_channels = 1
        chunk_size = 1
        device_name = "dummy"

        def __init__(self):
            self.calls = 0

        def read(self):
            if self.calls == 0:
                self.calls += 1
                return np.ones((1, 1), dtype=np.float32)
            return np.zeros((0, 1), dtype=np.float32)

    patch = patch_mod.ObliquePatch(lambda t: None)
    engine = engine_mod.ObliqueEngine(patch)
    engine.running = True
    engine._audio_stream_playback(DummyInput())
    assert len(writes) == 1


def test_list_monitors():
    setup_stubs()
    import types
    import glfw
    engine_mod = load_module("core.oblique_engine", ROOT / "core" / "oblique_engine.py")

    monitors = [object()]
    glfw.get_monitors = lambda: monitors
    glfw.get_monitor_name = lambda m: "Test"
    video_mode = types.SimpleNamespace(size=(800, 600), refresh_rate=60)
    glfw.get_video_mode = lambda m: video_mode

    engine_mod.ObliqueEngine.list_monitors()
