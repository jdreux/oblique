import sys
from collections import OrderedDict
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

    renderer._shader_cache["test"] = renderer.ShaderCacheEntry(
        Dummy("program"), Dummy("vao"), Dummy("vbo"), 0.0
    )
    renderer.cleanup_shader_cache()
    assert renderer._shader_cache == {}
    assert all(released.values())


def test_cleanup_last_good_cache():
    setup_stubs()
    renderer = load_module("core.renderer", ROOT / "core" / "renderer.py")

    released = {"program": False, "vao": False, "vbo": False}

    class Dummy:
        def __init__(self, key):
            self.key = key

        def release(self):
            released[self.key] = True

    renderer._shader_cache.clear()
    renderer._last_good_cache["test"] = renderer.ShaderCacheEntry(
        Dummy("program"), Dummy("vao"), Dummy("vbo"), 0.0
    )
    renderer.cleanup_last_good_cache()
    assert renderer._last_good_cache == {}
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


def test_shader_compile_falls_back_to_last_good(tmp_path, monkeypatch):
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
    renderer._last_good_cache.clear()

    renderer.render_fullscreen_quad(ctx, str(shader_file), {})
    fallback_entry = renderer._shader_cache[str(shader_file)]
    warnings: list[str] = []
    monkeypatch.setattr(renderer, "warning", lambda message: warnings.append(message))

    def broken_program(*args, **kwargs):
        raise moderngl.Error("compile error")

    monkeypatch.setattr(ctx, "program", broken_program)
    time.sleep(1)
    shader_file.write_text(shader_src + "\n// changed")

    renderer.render_fullscreen_quad(ctx, str(shader_file), {})
    assert renderer._shader_cache[str(shader_file)] is fallback_entry
    assert renderer._last_good_cache[str(shader_file)] is fallback_entry
    assert warnings


def test_shader_compile_error_raises_without_fallback(tmp_path, monkeypatch):
    setup_stubs()
    renderer = load_module("core.renderer", ROOT / "core" / "renderer.py")
    import moderngl

    ctx = moderngl.create_context()
    shader_src = (ROOT / "shaders" / "passthrough.frag").read_text()
    shader_file = tmp_path / "temp.frag"
    shader_file.write_text(shader_src)

    renderer._shader_cache.clear()
    renderer._last_good_cache.clear()

    def broken_program(*args, **kwargs):
        raise moderngl.Error("compile error")

    monkeypatch.setattr(ctx, "program", broken_program)

    with pytest.raises(moderngl.Error):
        renderer.render_fullscreen_quad(ctx, str(shader_file), {})


def test_texture_cache_lru_enforces_capacity():
    setup_stubs()
    renderer = load_module("core.renderer", ROOT / "core" / "renderer.py")

    released: list[str] = []

    class DummyTexture:
        def __init__(self, key: str):
            self.key = key

        def release(self):
            released.append(self.key)

    renderer._texture_cache = OrderedDict(
        (f"key_{idx}", DummyTexture(f"key_{idx}")) for idx in range(70)
    )
    renderer._enforce_texture_cache_limit()

    assert len(renderer._texture_cache) == 64
    assert released == [f"key_{idx}" for idx in range(6)]


def test_debug_mode_logs_uniform_contract_mismatches(tmp_path, monkeypatch):
    setup_stubs()
    renderer = load_module("core.renderer", ROOT / "core" / "renderer.py")
    import moderngl

    ctx = moderngl.create_context()
    shader_src = (ROOT / "shaders" / "passthrough.frag").read_text()
    shader_file = tmp_path / "debug_mismatch.frag"
    shader_file.write_text(shader_src)

    class DummyProgram(dict):
        def __iter__(self):
            return iter(["u_brightness", "u_resolution", "in_vert", "in_uv"])

        def release(self):
            return None

    monkeypatch.setattr(
        ctx,
        "program",
        lambda *args, **kwargs: DummyProgram({"u_brightness": None, "u_resolution": None}),
    )

    warnings: list[str] = []
    monkeypatch.setattr(renderer, "warning", lambda message: warnings.append(message))

    renderer._shader_cache.clear()
    renderer._last_good_cache.clear()
    renderer.set_debug_mode(True)
    renderer.render_fullscreen_quad(
        ctx,
        str(shader_file),
        {"u_brightnes": 0.5, "u_resolution": (1, 1)},
    )

    assert any("Python provides but shader ignores" in message for message in warnings)
    assert any("Shader expects but Python doesn't provide" in message for message in warnings)


def test_render_fullscreen_quad_preserves_input_texture_filter(monkeypatch):
    setup_stubs()
    renderer = load_module("core.renderer", ROOT / "core" / "renderer.py")
    import moderngl

    ctx = moderngl.create_context()

    class DummyProgram(dict):
        def release(self):
            return None

    monkeypatch.setattr(
        ctx,
        "program",
        lambda *args, **kwargs: DummyProgram(
            {"u_texture": None, "u_time": None, "u_resolution": None}
        ),
    )

    texture = moderngl.Texture()
    texture.filter = ("custom", "custom")

    renderer._shader_cache.clear()
    renderer._last_good_cache.clear()
    shader_path = str(resolve_asset_path("shaders/passthrough.frag"))
    renderer.render_fullscreen_quad(
        ctx,
        shader_path,
        {"u_texture": texture, "u_time": 0.0, "u_resolution": (1, 1)},
    )

    assert texture.filter == ("custom", "custom")
