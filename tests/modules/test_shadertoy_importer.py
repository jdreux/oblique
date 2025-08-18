from pathlib import Path

from tests.utils.stubs import load_module, setup_stubs

ROOT = Path(__file__).resolve().parents[2]


def test_shadertoy_uniform_mapping():
    setup_stubs()
    mod = load_module(
        "modules.utility.shadertoy_importer",
        ROOT / "modules" / "utility" / "shadertoy_importer.py",
    )
    ShadertoyParams = mod.ShadertoyParams
    ShadertoyModule = mod.ShadertoyModule

    import moderngl

    tex = moderngl.Texture()
    params = ShadertoyParams(
        width=100,
        height=50,
        frag_shader_path="shaders/passthrough.frag",
        iChannel0=tex,
    )
    module = ShadertoyModule(params)

    uniforms = module.prepare_uniforms(1.0)
    assert uniforms["iResolution"] == (100, 50, 2.0)
    assert uniforms["iTime"] == 1.0
    assert uniforms["iChannel0"] is tex
