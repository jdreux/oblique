from dataclasses import dataclass
from pathlib import Path
import sys

import pytest

from core.paths import resolve_asset_path
from tests.utils.stubs import load_module, setup_stubs


ROOT = Path(__file__).resolve().parents[2]


def _make_module():
    setup_stubs()
    base_mod = sys.modules.get("modules.core.base_av_module")
    if base_mod is None:
        base_mod = load_module("modules.core.base_av_module", ROOT / "modules/core/base_av_module.py")
    BaseAVModule = base_mod.BaseAVModule
    BaseAVParams = base_mod.BaseAVParams
    Uniforms = base_mod.Uniforms

    @dataclass
    class Params(BaseAVParams):
        width: int = 1
        height: int = 1

    class DummyModule(BaseAVModule[Params, Uniforms]):
        frag_shader_path = str(resolve_asset_path("shaders/passthrough.frag"))

        def prepare_uniforms(self, t: float) -> Uniforms:
            return {}

    return DummyModule(Params())


def test_resolve_param():
    setup_stubs()
    module = _make_module()
    base_mod = sys.modules["modules.core.base_av_module"]
    BaseProcessingOperator = base_mod.BaseProcessingOperator

    assert module._resolve_param(lambda: 3) == 3

    class DummyOperator(BaseProcessingOperator[int]):
        def process(self) -> int:
            return 7

    assert module._resolve_param(DummyOperator()) == 7


def test_resolve_param_prefers_processing_operator_over_callable():
    setup_stubs()
    module = _make_module()
    base_mod = sys.modules["modules.core.base_av_module"]
    BaseProcessingOperator = base_mod.BaseProcessingOperator

    class CallableOperator(BaseProcessingOperator[int]):
        def __call__(self) -> int:
            return 3

        def process(self) -> int:
            return 11

    assert module._resolve_param(CallableOperator()) == 11


def test_resolve_texture_param():
    setup_stubs()
    import moderngl

    module = _make_module()
    tex = moderngl.Texture()

    # Child module rendering to texture
    child = _make_module()
    child.render_texture = lambda ctx, w, h, t, filter=0: tex  # type: ignore[attr-defined]

    resolved = module._resolve_texture_param(child, moderngl.create_context(), 1, 1, 0.0, 0)
    assert resolved is tex

    resolved_list = module._resolve_texture_param([child, child], moderngl.create_context(), 1, 1, 0.0, 0)
    assert resolved_list == [tex, tex]


def test_render_texture_invokes_renderer(monkeypatch):
    setup_stubs()
    import moderngl
    renderer = load_module("core.renderer", ROOT / "core" / "renderer.py")

    module = _make_module()
    dummy_tex = moderngl.Texture()

    called = {}

    def fake_render_to_texture(module_arg, width, height, frag_shader_path, uniforms, filter, cache_tag):
        called["args"] = (module_arg, width, height, frag_shader_path, uniforms)
        return dummy_tex

    base_mod = sys.modules["modules.core.base_av_module"]
    monkeypatch.setattr(base_mod, "render_to_texture", fake_render_to_texture)

    ctx = moderngl.create_context()
    result = module.render_texture(ctx, 2, 3, 0.1)
    assert result is dummy_tex
    assert called["args"][0] is module
    assert called["args"][1:4] == (2, 3, module.frag_shader_path)
    assert called["args"][4]["u_resolution"] == (2, 3)


def test_ping_pong_history_evicts_stale_resolution(monkeypatch):
    setup_stubs()
    import moderngl

    base_mod = sys.modules.get("modules.core.base_av_module")
    if base_mod is None:
        base_mod = load_module(
            "modules.core.base_av_module",
            ROOT / "modules/core/base_av_module.py",
        )

    BaseAVModule = base_mod.BaseAVModule
    BaseAVParams = base_mod.BaseAVParams
    Uniforms = base_mod.Uniforms

    @dataclass
    class Params(BaseAVParams):
        width: int = 1
        height: int = 1

    class PingPongModule(BaseAVModule[Params, Uniforms]):
        frag_shader_path = str(resolve_asset_path("shaders/passthrough.frag"))
        ping_pong = True
        previous_uniform_name = "u_previous"

        def prepare_uniforms(self, t: float) -> Uniforms:
            return {}

    module = PingPongModule(Params())

    class DummyTexture:
        def __init__(self, label: str):
            self.label = label
            self.released = False

        def release(self):
            self.released = True

    created: list[DummyTexture] = []
    released: list[DummyTexture] = []

    def fake_render_to_texture(
        module_arg,
        width,
        height,
        frag_shader_path,
        uniforms,
        filter,
        cache_tag,
    ):
        tex = DummyTexture(f"{cache_tag}:{width}x{height}")
        created.append(tex)
        return tex

    def fake_release_texture_reference(texture):
        released.append(texture)
        texture.release()

    monkeypatch.setattr(base_mod, "render_to_texture", fake_render_to_texture)
    monkeypatch.setattr(base_mod, "release_texture_reference", fake_release_texture_reference)

    ctx = moderngl.create_context()
    module.render_texture(ctx, 800, 600, 0.0)
    module.render_texture(ctx, 800, 600, 0.1)
    assert any(key.endswith("800x600") for key in module._texture_history)

    module.render_texture(ctx, 1920, 1080, 0.2)
    assert module._texture_history
    assert all(key.endswith("1920x1080") for key in module._texture_history)
    assert released
    assert all(tex.released for tex in released)


def test_texture_pass_uniforms_require_explicit_u_prefix(monkeypatch):
    setup_stubs()
    import moderngl

    base_mod = sys.modules.get("modules.core.base_av_module")
    if base_mod is None:
        base_mod = load_module(
            "modules.core.base_av_module",
            ROOT / "modules/core/base_av_module.py",
        )

    BaseAVModule = base_mod.BaseAVModule
    BaseAVParams = base_mod.BaseAVParams
    TexturePass = base_mod.TexturePass
    Uniforms = base_mod.Uniforms

    @dataclass
    class Params(BaseAVParams):
        width: int = 1
        height: int = 1

    class DummyModule(BaseAVModule[Params, Uniforms]):
        frag_shader_path = str(resolve_asset_path("shaders/passthrough.frag"))
        aux_pass = TexturePass(
            frag_shader_path=str(resolve_asset_path("shaders/passthrough.frag")),
            uniforms={"plain_key": 123},
            name="aux",
        )

        def prepare_uniforms(self, t: float) -> Uniforms:
            return {
                "u_aux": self.aux_pass,
            }

    recorded_uniforms: list[dict] = []

    def fake_render_to_texture(
        module_arg,
        width,
        height,
        frag_shader_path,
        uniforms,
        filter,
        cache_tag,
    ):
        recorded_uniforms.append(dict(uniforms))
        return moderngl.Texture()

    monkeypatch.setattr(base_mod, "render_to_texture", fake_render_to_texture)

    module = DummyModule(Params())
    module.render_texture(moderngl.create_context(), 4, 4, 0.0)

    assert recorded_uniforms
    assert any("plain_key" in uniforms for uniforms in recorded_uniforms)
    assert all("u_plain_key" not in uniforms for uniforms in recorded_uniforms)


def test_texture_pass_can_opt_out_of_parent_uniform_inheritance(monkeypatch):
    setup_stubs()
    import moderngl

    base_mod = sys.modules.get("modules.core.base_av_module")
    if base_mod is None:
        base_mod = load_module(
            "modules.core.base_av_module",
            ROOT / "modules/core/base_av_module.py",
        )

    BaseAVModule = base_mod.BaseAVModule
    BaseAVParams = base_mod.BaseAVParams
    TexturePass = base_mod.TexturePass
    Uniforms = base_mod.Uniforms

    @dataclass
    class Params(BaseAVParams):
        width: int = 1
        height: int = 1

    class DummyModule(BaseAVModule[Params, Uniforms]):
        frag_shader_path = str(resolve_asset_path("shaders/passthrough.frag"))
        isolated_pass = TexturePass(
            frag_shader_path=str(resolve_asset_path("shaders/passthrough.frag")),
            uniforms={"u_local_only": 123.0},
            name="isolated",
            inherit_parent_uniforms=False,
        )

        def prepare_uniforms(self, t: float) -> Uniforms:
            return {
                "u_time": t,
                "u_parent_value": 42.0,
                "u_isolated": self.isolated_pass,
            }

    captured_by_tag: dict[str, dict] = {}

    def fake_render_to_texture(
        module_arg,
        width,
        height,
        frag_shader_path,
        uniforms,
        filter,
        cache_tag,
    ):
        captured_by_tag[cache_tag] = dict(uniforms)
        return moderngl.Texture()

    monkeypatch.setattr(base_mod, "render_to_texture", fake_render_to_texture)

    module = DummyModule(Params())
    module.render_texture(moderngl.create_context(), 4, 4, 1.5)

    assert "isolated" in captured_by_tag
    isolated_uniforms = captured_by_tag["isolated"]
    assert isolated_uniforms["u_resolution"] == (4, 4)
    assert isolated_uniforms["u_local_only"] == pytest.approx(123.0)
    assert "u_parent_value" not in isolated_uniforms
    assert "u_time" not in isolated_uniforms


def test_texture_pass_filter_override_is_opt_in(monkeypatch):
    setup_stubs()
    import moderngl

    base_mod = sys.modules.get("modules.core.base_av_module")
    if base_mod is None:
        base_mod = load_module(
            "modules.core.base_av_module",
            ROOT / "modules/core/base_av_module.py",
        )

    BaseAVModule = base_mod.BaseAVModule
    BaseAVParams = base_mod.BaseAVParams
    TexturePass = base_mod.TexturePass
    Uniforms = base_mod.Uniforms

    @dataclass
    class Params(BaseAVParams):
        width: int = 1
        height: int = 1

    class DummyModule(BaseAVModule[Params, Uniforms]):
        frag_shader_path = str(resolve_asset_path("shaders/passthrough.frag"))

        def prepare_uniforms(self, t: float) -> Uniforms:
            return {}

    recorded_filters: list[int] = []

    def fake_render_to_texture(
        module_arg,
        width,
        height,
        frag_shader_path,
        uniforms,
        filter,
        cache_tag,
    ):
        recorded_filters.append(filter)
        return moderngl.Texture()

    monkeypatch.setattr(base_mod, "render_to_texture", fake_render_to_texture)

    module = DummyModule(Params())
    module.texture_pass.filter = moderngl.LINEAR
    module.render_texture(moderngl.create_context(), 4, 4, 0.0, filter=moderngl.NEAREST)

    assert recorded_filters == [moderngl.LINEAR]
