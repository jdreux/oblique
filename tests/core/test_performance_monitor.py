import importlib.util
import sys
import time
import types
from pathlib import Path

import pytest


def load_performance_monitor():
    sys.modules.setdefault("moderngl", types.ModuleType("moderngl"))
    core_pkg = types.ModuleType("core")
    core_pkg.__path__ = []
    sys.modules.setdefault("core", core_pkg)
    logger_module = types.ModuleType("core.logger")
    logger_module.debug = lambda *args, **kwargs: None
    sys.modules["core.logger"] = logger_module
    path = Path(__file__).resolve().parents[2] / "core" / "performance_monitor.py"
    spec = importlib.util.spec_from_file_location("core.performance_monitor", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["core.performance_monitor"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.PerformanceMonitor


PerformanceMonitor = load_performance_monitor()


def test_performance_monitor_stats(monkeypatch):
    pm = PerformanceMonitor(window_size=2)

    times = iter([0.0, 0.01, 0.02, 0.03, 0.04, 0.05])
    monkeypatch.setattr(time, "time", lambda: next(times))

    pm.begin_frame()
    pm.end_frame()
    pm.begin_frame()
    pm.end_frame()

    stats = pm.get_stats()
    assert stats["frame_count"] == 2
    assert stats["avg_fps"] == pytest.approx(100.0, abs=1)
    assert stats["min_fps"] == pytest.approx(100.0, abs=1)
    assert stats["max_fps"] == pytest.approx(100.0, abs=1)

    pm.reset()
    assert pm.frame_count == 0
