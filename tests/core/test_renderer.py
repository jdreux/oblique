import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

import pytest
from pathlib import Path
from tests.utils.stubs import setup_stubs, load_module


ROOT = Path(__file__).resolve().parents[2]


def test_set_debug_mode_and_ctx():
    setup_stubs()
    renderer = load_module("core.renderer", ROOT / "core" / "renderer.py")

    ctx = object()
    renderer.set_debug_mode(True)
    assert renderer._debug_mode is True
    renderer.set_ctx(ctx)  # type: ignore[arg-type]
    assert renderer._ctx is ctx


def test_cleanup_shader_cache():
    setup_stubs()
    renderer = load_module("core.renderer", ROOT / "core" / "renderer.py")

    released = {"program": False, "vao": False, "vbo": False}

    class Dummy:
        def __init__(self, key):
            self.key = key

        def release(self):
            released[self.key] = True

    renderer._shader_cache["test"] = (Dummy("program"), Dummy("vao"), Dummy("vbo"))
    renderer.cleanup_shader_cache()
    assert renderer._shader_cache == {}
    assert all(released.values())


def test_render_to_texture_requires_ctx():
    setup_stubs()
    renderer = load_module("core.renderer", ROOT / "core" / "renderer.py")
    renderer._ctx = None
    with pytest.raises(RuntimeError):
        renderer.render_to_texture(object(), 1, 1, "shaders/passthrough.frag", {}, 0)


def test_blend_textures_requires_ctx():
    setup_stubs()
    renderer = load_module("core.renderer", ROOT / "core" / "renderer.py")
    import moderngl

    renderer._ctx = None
    tex = moderngl.Texture()
    with pytest.raises(RuntimeError):
        renderer.blend_textures(1, 1, tex, tex, "shaders/additive-blend.frag")


def test_render_fullscreen_quad_caches():
    setup_stubs()
    renderer = load_module("core.renderer", ROOT / "core" / "renderer.py")
    import moderngl

    ctx = moderngl.create_context()
    shader_path = "shaders/passthrough.frag"
    renderer._shader_cache.clear()
    renderer.render_fullscreen_quad(ctx, shader_path, {})
    assert shader_path in renderer._shader_cache
    renderer.render_fullscreen_quad(ctx, shader_path, {})
    assert len(renderer._shader_cache) == 1
