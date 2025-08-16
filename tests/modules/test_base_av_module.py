from pathlib import Path
from dataclasses import dataclass
import sys
import pytest
from tests.utils.stubs import setup_stubs, load_module


ROOT = Path(__file__).resolve().parents[2]


def _make_module():
    setup_stubs()
    load_module("core.oblique_node", ROOT / "core" / "oblique_node.py")
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
        frag_shader_path = "shaders/passthrough.frag"

        def prepare_uniforms(self, t: float) -> Uniforms:
            return {}

    return DummyModule(Params())


def test_resolve_param():
    setup_stubs()
    load_module("core.oblique_node", ROOT / "core" / "oblique_node.py")
    module = _make_module()
    base_mod = sys.modules["modules.core.base_av_module"]
    BaseProcessingOperator = base_mod.BaseProcessingOperator

    assert module._resolve_param(lambda: 3) == 3

    class DummyOperator(BaseProcessingOperator[int]):
        def process(self) -> int:
            return 7

    assert module._resolve_param(DummyOperator()) == 7


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
