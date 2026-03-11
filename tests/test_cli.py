"""Tests for the top-level CLI helpers."""

from argparse import Namespace
from types import ModuleType
import importlib
import sys

import pytest

# ``cli`` imports ``sounddevice`` via ``core.oblique_engine``; provide a stub so
# the tests don't require native PortAudio bindings.
sys.modules.setdefault("sounddevice", ModuleType("sounddevice"))

logger_module = sys.modules.get("core.logger")
if logger_module is None:
    logger_module = importlib.import_module("core.logger")
elif not hasattr(logger_module, "configure_logging"):
    logger_module.configure_logging = lambda *args, **kwargs: None  # type: ignore[attr-defined]
    logger_module.error = getattr(logger_module, "error", lambda *a, **k: None)
    logger_module.info = getattr(logger_module, "info", lambda *a, **k: None)
    logger_module.warning = getattr(logger_module, "warning", lambda *a, **k: None)

import cli as cli_module
from cli import CliError, ExitCode, resolve_start_configuration, run_render


def test_start_requires_patch_argument() -> None:
    """``oblique start`` must refuse to run without an explicit patch target."""

    args = Namespace(
        target=None,
        extra_target=None,
        width=800,
        height=600,
        fps=60,
        monitor=None,
        hot_reload_shaders=False,
        hot_reload_python=False,
        log_level="INFO",
        log_file=None,
    )

    with pytest.raises(CliError) as err:
        resolve_start_configuration(args)

    assert err.value.exit_code == ExitCode.USAGE


def test_start_python_reload_only_allowed_for_repl() -> None:
    """Requesting Python hot reload outside the REPL should fail fast."""

    args = Namespace(
        target="projects.demo.demo_audio_file",
        extra_target=None,
        width=800,
        height=600,
        fps=60,
        monitor=None,
        hot_reload_shaders=False,
        hot_reload_python=True,
        log_level="INFO",
        log_file=None,
    )

    with pytest.raises(CliError) as err:
        resolve_start_configuration(args)

    assert err.value.exit_code == ExitCode.USAGE


def _render_args(**overrides: object) -> Namespace:
    defaults = {
        "target": "projects.demo.demo_audio_file",
        "t": 0.0,
        "output": None,
        "output_dir": None,
        "duration": None,
        "frames": None,
        "fps": 30,
        "width": 800,
        "height": 600,
        "prime_audio": 0.5,
        "inspect": False,
        "log_level": "WARNING",
    }
    defaults.update(overrides)
    return Namespace(**defaults)


def test_render_rejects_duration_and_frames_together() -> None:
    args = _render_args(output_dir="/tmp/frames", duration=1.0, frames=10)
    assert run_render(args) == ExitCode.USAGE


def test_render_rejects_non_positive_fps() -> None:
    args = _render_args(output_dir="/tmp/frames", frames=2, fps=0)
    assert run_render(args) == ExitCode.USAGE


def test_render_video_uses_fps_timeline_for_frame_count(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, object] = {}

    class FakeHeadlessRenderer:
        def __init__(self, patch: object, width: int, height: int) -> None:
            self.patch = patch
            self.width = width
            self.height = height

        def __enter__(self) -> "FakeHeadlessRenderer":
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def prime_audio(self, t: float) -> None:
            calls["prime_audio"] = t

        def render_video(self, start_t: float, end_t: float, fps: int, output: str) -> None:
            calls["render_video"] = (start_t, end_t, fps, output)

        def render_to_file(self, _: float, __: str) -> None:  # pragma: no cover - safety net
            raise AssertionError("render_to_file should not be called")

        def render_sequence(
            self,
            _: list[float],
            __: str,
        ) -> None:  # pragma: no cover - safety net
            raise AssertionError("render_sequence should not be called")

    fake_module = ModuleType("core.headless_renderer")
    fake_module.HeadlessRenderer = FakeHeadlessRenderer
    monkeypatch.setitem(sys.modules, "core.headless_renderer", fake_module)
    monkeypatch.setattr(cli_module, "parse_patch_reference", lambda _: object())
    monkeypatch.setattr(
        cli_module,
        "instantiate_patch",
        lambda *_args, **_kwargs: (object(), None, None),
    )

    args = _render_args(
        t=1.5,
        output="/tmp/out.mp4",
        frames=10,
        fps=20,
    )
    assert run_render(args) == ExitCode.OK

    start_t, end_t, fps, output = calls["render_video"]  # type: ignore[misc]
    assert start_t == pytest.approx(1.5)
    assert end_t == pytest.approx(2.0)
    assert fps == 20
    assert output == "/tmp/out.mp4"
