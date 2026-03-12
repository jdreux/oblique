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
        "debug": False,
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


def test_render_inspect_prints_json_for_single_frame(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
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
            return None

        def inspect(self, t: float) -> dict[str, object]:
            return {"mode": "single", "t": t}

        def inspect_sequence(self, times: list[float]) -> dict[str, object]:  # pragma: no cover - safety
            raise AssertionError("inspect_sequence should not be called")

    fake_module = ModuleType("core.headless_renderer")
    fake_module.HeadlessRenderer = FakeHeadlessRenderer
    monkeypatch.setitem(sys.modules, "core.headless_renderer", fake_module)
    monkeypatch.setattr(cli_module, "parse_patch_reference", lambda _: object())
    monkeypatch.setattr(
        cli_module,
        "instantiate_patch",
        lambda *_args, **_kwargs: (object(), None, None),
    )

    args = _render_args(inspect=True, t=1.25)
    assert run_render(args) == ExitCode.OK

    out = capsys.readouterr().out
    assert '"mode": "single"' in out
    assert '"t": 1.25' in out


def test_render_inspect_uses_temporal_analysis_for_multi_frame(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
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
            return None

        def inspect(self, t: float) -> dict[str, object]:  # pragma: no cover - safety
            raise AssertionError("inspect should not be called")

        def inspect_sequence(self, times: list[float]) -> dict[str, object]:
            calls["times"] = times
            return {"mode": "temporal", "motion_profile": [0.1, 0.2]}

    fake_module = ModuleType("core.headless_renderer")
    fake_module.HeadlessRenderer = FakeHeadlessRenderer
    monkeypatch.setitem(sys.modules, "core.headless_renderer", fake_module)
    monkeypatch.setattr(cli_module, "parse_patch_reference", lambda _: object())
    monkeypatch.setattr(
        cli_module,
        "instantiate_patch",
        lambda *_args, **_kwargs: (object(), None, None),
    )

    args = _render_args(inspect=True, t=0.0, frames=3, fps=10)
    assert run_render(args) == ExitCode.OK

    out = capsys.readouterr().out
    assert '"mode": "temporal"' in out
    assert calls["times"] == pytest.approx([0.0, 0.1, 0.2])  # type: ignore[arg-type]


def test_parser_supports_module_registry_commands() -> None:
    parser = cli_module.build_parser()
    args = parser.parse_args(
        ["list-modules", "--json", "--tag", "feedback", "--category", "effects"]
    )
    assert args.command == "list-modules"
    assert args.json is True
    assert args.tag == ["feedback"]
    assert args.category == "effects"

    describe_args = parser.parse_args(["describe", "FeedbackModule", "--json"])
    assert describe_args.command == "describe"
    assert describe_args.module_name == "FeedbackModule"
    assert describe_args.json is True


def test_parser_supports_debug_flags() -> None:
    parser = cli_module.build_parser()
    start_args = parser.parse_args(["start", "projects.demo.demo_audio_file", "--debug"])
    assert start_args.command == "start"
    assert start_args.debug is True

    render_args = parser.parse_args(["render", "projects.demo.demo_audio_file", "--debug", "--inspect"])
    assert render_args.command == "render"
    assert render_args.debug is True

def test_list_modules_json_output(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    class DummySpec:
        name = "FeedbackModule"
        category = "effects"
        description = "Feedback module"
        tags = ["feedback"]
        params = []
        inputs = ["input_texture"]
        outputs = ["texture"]
        cost_hint = "low"
        shader_path = "modules/effects/shaders/feedback.frag"
        module_class = "modules.effects.feedback.FeedbackModule"

    fake_registry = ModuleType("core.registry")
    fake_registry.discover_modules = lambda: {"FeedbackModule": DummySpec()}
    fake_registry.search_modules = lambda query, tags, category: [DummySpec()]
    fake_registry.module_spec_to_dict = lambda spec: {
        "name": spec.name,
        "category": spec.category,
        "description": spec.description,
        "tags": spec.tags,
        "params": spec.params,
        "inputs": spec.inputs,
        "outputs": spec.outputs,
        "cost_hint": spec.cost_hint,
        "shader_path": spec.shader_path,
        "module_class": spec.module_class,
    }
    monkeypatch.setitem(sys.modules, "core.registry", fake_registry)

    args = Namespace(json=True, tag=[], category=None)
    assert cli_module.run_list_modules(args) == ExitCode.OK
    out = capsys.readouterr().out
    assert '"name": "FeedbackModule"' in out


def test_describe_unknown_module_returns_usage(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_registry = ModuleType("core.registry")
    fake_registry.discover_modules = lambda: {}
    fake_registry.get_registry = lambda: {}
    fake_registry.module_spec_to_dict = lambda spec: spec
    monkeypatch.setitem(sys.modules, "core.registry", fake_registry)

    args = Namespace(module_name="UnknownModule", json=False)
    assert cli_module.run_describe(args) == ExitCode.USAGE
    err = capsys.readouterr().err
    assert "unknown module" in err


def test_render_debug_calls_set_debug_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    debug_calls: list[bool] = []

    fake_renderer_mod = ModuleType("core.renderer")
    fake_renderer_mod.set_debug_mode = lambda enabled: debug_calls.append(enabled)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "core.renderer", fake_renderer_mod)

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
            return None

        def inspect(self, t: float) -> dict[str, object]:
            return {"ok": True}

    fake_headless = ModuleType("core.headless_renderer")
    fake_headless.HeadlessRenderer = FakeHeadlessRenderer
    monkeypatch.setitem(sys.modules, "core.headless_renderer", fake_headless)
    monkeypatch.setattr(cli_module, "parse_patch_reference", lambda _: object())
    monkeypatch.setattr(
        cli_module,
        "instantiate_patch",
        lambda *_args, **_kwargs: (object(), None, None),
    )

    args = _render_args(inspect=True, debug=True)
    assert run_render(args) == ExitCode.OK
    assert debug_calls == [True]
