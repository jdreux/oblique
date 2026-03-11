from pathlib import Path

from tests.utils.stubs import load_module, setup_stubs


ROOT = Path(__file__).resolve().parents[2]


def test_composite_default_mix_uniform():
    setup_stubs()
    composite_module = load_module(
        "modules.composition.composite_module",
        ROOT / "modules/composition/composite_module.py",
    )
    import moderngl

    top = moderngl.Texture()
    bottom = moderngl.Texture()
    params = composite_module.CompositeParams(
        width=800,
        height=600,
        top_texture=top,
        bottom_texture=bottom,
    )
    module = composite_module.CompositeModule(params)

    uniforms = module.prepare_uniforms(0.0)
    assert uniforms["u_op"] == int(composite_module.CompositeOp.ADD)
    assert uniforms["u_mix"] == 1.0
    assert uniforms["top_tex"] is top
    assert uniforms["bottom_tex"] is bottom


def test_composite_resolves_callable_mix():
    setup_stubs()
    composite_module = load_module(
        "modules.composition.composite_module",
        ROOT / "modules/composition/composite_module.py",
    )
    import moderngl

    calls = {"mix": 0}

    def mix_value() -> float:
        calls["mix"] += 1
        return 0.25

    params = composite_module.CompositeParams(
        width=640,
        height=360,
        top_texture=moderngl.Texture(),
        bottom_texture=moderngl.Texture(),
        operation=composite_module.CompositeOp.SCREEN,
        mix=mix_value,
    )
    module = composite_module.CompositeModule(params)

    uniforms = module.prepare_uniforms(0.0)
    assert uniforms["u_mix"] == 0.25
    assert calls["mix"] == 1


def test_composite_shader_contains_mix_crossfade():
    shader_src = (ROOT / "modules/composition/shaders/composite.frag").read_text()
    assert "uniform float u_mix;" in shader_src
    assert "result = mix(bottom, result, u_mix);" in shader_src
