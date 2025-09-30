import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import pytest

from core.paths import resolve_asset_path
from tests.utils.stubs import load_module, setup_stubs


ROOT = Path(__file__).resolve().parents[2]


def test_set_hot_reload_and_ctx():
    setup_stubs()
    renderer = load_module("core.renderer", ROOT / "core" / "renderer.py")

    ctx = object()
    renderer.set_hot_reload_shaders(True)
    assert renderer._hot_reload_shaders_enabled is True
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

    renderer._shader_cache["test"] = renderer.ShaderCacheEntry(
        Dummy("program"), Dummy("vao"), Dummy("vbo"), 0.0
    )
    renderer.cleanup_shader_cache()
    assert renderer._shader_cache == {}
    assert all(released.values())


def test_render_to_texture_requires_ctx():
    setup_stubs()
    renderer = load_module("core.renderer", ROOT / "core" / "renderer.py")
    renderer._ctx = None
    with pytest.raises(RuntimeError):
        renderer.render_to_texture(
            object(),
            1,
            1,
            str(resolve_asset_path("shaders/passthrough.frag")),
            {},
            0,
        )


def test_blend_textures_requires_ctx():
    setup_stubs()
    renderer = load_module("core.renderer", ROOT / "core" / "renderer.py")
    import moderngl

    renderer._ctx = None
    tex = moderngl.Texture()
    with pytest.raises(RuntimeError):
        renderer.blend_textures(
            1,
            1,
            tex,
            tex,
            str(resolve_asset_path("shaders/additive-blend.frag")),
        )


def test_render_fullscreen_quad_caches():
    setup_stubs()
    renderer = load_module("core.renderer", ROOT / "core" / "renderer.py")
    import moderngl

    ctx = moderngl.create_context()
    shader_path = str(resolve_asset_path("shaders/passthrough.frag"))
    renderer._shader_cache.clear()
    renderer.render_fullscreen_quad(ctx, shader_path, {})
    assert shader_path in renderer._shader_cache
    renderer.render_fullscreen_quad(ctx, shader_path, {})
    assert len(renderer._shader_cache) == 1


def test_hot_reload_only_on_change(tmp_path):
    setup_stubs()
    renderer = load_module("core.renderer", ROOT / "core" / "renderer.py")
    import moderngl
    import time

    ctx = moderngl.create_context()
    shader_src = (ROOT / "shaders" / "passthrough.frag").read_text()
    shader_file = tmp_path / "temp.frag"
    shader_file.write_text(shader_src)

    renderer.set_hot_reload_shaders(True)
    renderer._shader_cache.clear()

    renderer.render_fullscreen_quad(ctx, str(shader_file), {})
    first_program = renderer._shader_cache[str(shader_file)].program

    renderer.render_fullscreen_quad(ctx, str(shader_file), {})
    second_program = renderer._shader_cache[str(shader_file)].program
    assert first_program is second_program

    time.sleep(1)
    shader_file.write_text(shader_src + "\n// mod")

    renderer.render_fullscreen_quad(ctx, str(shader_file), {})
    third_program = renderer._shader_cache[str(shader_file)].program
    assert third_program is not first_program
