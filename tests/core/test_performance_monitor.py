import importlib.util
import time
from pathlib import Path

import pytest

from tests.utils.stubs import setup_stubs, load_module


def load_performance_monitor():
    setup_stubs()
    path = Path(__file__).resolve().parents[2] / "core" / "performance_monitor.py"
    module = load_module("core.performance_monitor", path)
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
