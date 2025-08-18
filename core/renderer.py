"""Rendering helpers for Oblique's Shadertoy‑style pipeline.

The renderer draws a fullscreen quad using a fixed vertex shader while fragment
shaders provide all visual logic.  It also offers utilities for off‑screen
passes and ping‑pong rendering used by :class:`~modules.core.base_av_module.BaseAVModule`.
The implementation targets OpenGL 3.3 / GLSL 330 and is primarily tested on
Apple Silicon.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import moderngl
import numpy as np
import os

from core.logger import error, warning
from core.shader_preprocessor import preprocess_shader

if TYPE_CHECKING:
    from modules.core.base_av_module import BaseAVModule, Uniforms

@dataclass
class ShaderCacheEntry:
    """Container for shader resources cached by this module."""

    program: moderngl.Program
    vao: moderngl.VertexArray
    vbo: moderngl.Buffer
    mtime: float


_shader_cache: dict[str, ShaderCacheEntry] = {}
_texture_cache: dict[str, moderngl.Texture] = {}
_hot_reload_shaders_enabled = False
_ctx: moderngl.Context | None = None


def set_hot_reload_shaders(enabled: bool) -> None:
    """Enable or disable automatic shader reloading.

    When enabled, shaders are reloaded from disk every time ``render_fullscreen_quad``
    or ``blend_textures`` is called, bypassing the internal shader cache.

    Args:
        enabled: If ``True``, always reload shaders from file.
    """
    global _hot_reload_shaders_enabled
    _hot_reload_shaders_enabled = enabled

def set_ctx(ctx: moderngl.Context) -> None:
    """
    Set the context globally.
    """
    global _ctx
    _ctx = ctx

def cleanup_shader_cache() -> None:
    """Release all cached shader resources.

    Call this when shutting down the application to avoid leaking GPU resources.
    """
    global _shader_cache
    for entry in _shader_cache.values():
        _release_shader_cache_entry(entry)
    _shader_cache.clear()


def _release_shader_cache_entry(entry: ShaderCacheEntry) -> None:
    """Safely release program, VAO and VBO resources from a cache entry."""
    if entry is not None:
        try:
            entry.vao.release()
        except Exception:
            warning("Failed to release VAO")
        try:
            entry.vbo.release()
        except Exception:
            warning("Failed to release VBO")
        try:
            entry.program.release()
        except Exception:
            warning("Failed to release program")


def render_fullscreen_quad(
    ctx: moderngl.Context, frag_shader_path: str, uniforms: dict[str, Any]
) -> tuple[moderngl.Program, moderngl.VertexArray, moderngl.Buffer]:
    """Draw a fullscreen quad with a stock vertex shader.

    The fragment shader is compiled and paired with a minimal vertex shader that
    outputs a fullscreen triangle strip—mirroring Shadertoy where all creative
    logic lives in the fragment shader.  Compiled programs and buffers are
    cached for reuse.

    Returns
    -------
    tuple
        ``(program, vao, vbo)`` for optional manual management.
    """
    global _shader_cache, _hot_reload_shaders_enabled

    current_mtime = os.path.getmtime(frag_shader_path)
    if frag_shader_path in _shader_cache:
        cached = _shader_cache[frag_shader_path]
        if _hot_reload_shaders_enabled and current_mtime > cached.mtime:
            _release_shader_cache_entry(cached)
            del _shader_cache[frag_shader_path]

    if frag_shader_path not in _shader_cache:
        # Pre-process the shader to resolve includes
        fragment_shader = preprocess_shader(frag_shader_path)
        vertex_shader = """
            #version 330
            in vec2 in_vert;
            in vec2 in_uv;
            out vec2 v_uv;
            void main() {
                v_uv = in_uv;
                gl_Position = vec4(in_vert, 0.0, 1.0);
            }
        """
        program = ctx.program(
            vertex_shader=vertex_shader,
            fragment_shader=fragment_shader,
        )
        vertices = np.array(
            [
                -1.0,
                -1.0,
                0.0,
                0.0,
                1.0,
                -1.0,
                1.0,
                0.0,
                -1.0,
                1.0,
                0.0,
                1.0,
                1.0,
                1.0,
                1.0,
                1.0,
            ],
            dtype="f4",
        )
        vbo = ctx.buffer(vertices.tobytes())
        vao = ctx.simple_vertex_array(program, vbo, "in_vert", "in_uv")
        _shader_cache[frag_shader_path] = ShaderCacheEntry(program, vao, vbo, current_mtime)
    else:
        cached_entry = _shader_cache[frag_shader_path]
        program, vao, vbo = cached_entry.program, cached_entry.vao, cached_entry.vbo

    # Set uniforms efficiently
    texture_unit = 0
    for name, value in uniforms.items():
        if name in program:
            if isinstance(value, moderngl.Texture):
                # Optimize texture binding
                value.filter = (moderngl.LINEAR, moderngl.LINEAR)
                value.use(location=texture_unit)
                program[name] = texture_unit
                texture_unit += 1
            else:
                # Direct uniform assignment
                program[name] = value

    vao.render(moderngl.TRIANGLE_STRIP)
    return program, vao, vbo

def render_to_texture(
    module: "BaseAVModule",
    width: int,
    height: int,
    frag_shader_path: str,
    uniforms: "Uniforms",
    filter: int = moderngl.NEAREST,
    cache_tag: str = ""
) -> moderngl.Texture:
    """Render a module pass to an off‑screen texture.

    Used by modules to build feedback chains, ping‑pong buffers and other
    intermediate passes. Each pass uses the same stock vertex shader as
    :func:`render_fullscreen_quad`.

    The optional ``cache_tag`` creates distinct cache entries for multiple
    off‑screen passes of identical resolution within a module.
    """
    global _texture_cache
    global _ctx

    if _ctx is None:
        raise RuntimeError("OpenGL Context not set")

    cache_key = f"{module.__class__.__name__}_{cache_tag}_{width}_{height}_{filter}"

    if cache_key in _texture_cache:
        tex = _texture_cache[cache_key]
    else:
        tex = _ctx.texture((width, height), 4, dtype="f4", alignment=1)
        tex.filter = (filter, filter)
        tex.repeat_x = False
        tex.repeat_y = False

    fbo = _ctx.framebuffer(color_attachments=[tex])
    try:
        _ctx.viewport = (0, 0, width, height)
        fbo.use()
        _ctx.clear(0.0, 0.0, 0.0, 1.0)

        # Render the shader to the texture
        render_fullscreen_quad(_ctx, frag_shader_path, dict(uniforms))
    except Exception as e:
        error(f"Error rendering to texture: {e}")
        raise e
    finally:
        fbo.release()

    _texture_cache[cache_key] = tex

    return tex


def blend_textures(
    width: int,
    height: int,
    tex0: moderngl.Texture,
    tex1: moderngl.Texture,
    blend_shader_path: str,
) -> moderngl.Texture:
    """
    Blend two textures using the specified blend shader and return the result as a new texture.
    """
    global _ctx

    if _ctx is None:
        raise RuntimeError("OpenGL Context not set")

    ctx = _ctx
    out_tex = ctx.texture((width, height), 4, dtype="f1", alignment=1)
    out_tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
    out_tex.repeat_x = False
    out_tex.repeat_y = False

    fbo = ctx.framebuffer(color_attachments=[out_tex])
    try:
        ctx.viewport = (0, 0, width, height)
        fbo.use()
        ctx.clear(0.0, 0.0, 0.0, 1.0)

        global _shader_cache, _hot_reload_shaders_enabled

        current_mtime = os.path.getmtime(blend_shader_path)
        if blend_shader_path in _shader_cache:
            cached = _shader_cache[blend_shader_path]
            if _hot_reload_shaders_enabled and current_mtime > cached.mtime:
                _release_shader_cache_entry(cached)
                del _shader_cache[blend_shader_path]

        if blend_shader_path not in _shader_cache:
            # Pre-process the shader to resolve includes
            fragment_shader = preprocess_shader(blend_shader_path)
            vertex_shader = """
                #version 330
                in vec2 in_vert;
                in vec2 in_uv;
                out vec2 v_uv;
                void main() {
                    v_uv = in_uv;
                    gl_Position = vec4(in_vert, 0.0, 1.0);
                }
            """
            program = ctx.program(
                vertex_shader=vertex_shader,
                fragment_shader=fragment_shader,
            )
            vertices = np.array(
                [
                    -1.0,
                    -1.0,
                    0.0,
                    0.0,
                    1.0,
                    -1.0,
                    1.0,
                    0.0,
                    -1.0,
                    1.0,
                    0.0,
                    1.0,
                    1.0,
                    1.0,
                    1.0,
                    1.0,
                ],
                dtype="f4",
            )
            vbo = ctx.buffer(vertices.tobytes())
            vao = ctx.simple_vertex_array(program, vbo, "in_vert", "in_uv")
            _shader_cache[blend_shader_path] = ShaderCacheEntry(program, vao, vbo, current_mtime)
        else:
            cached_entry = _shader_cache[blend_shader_path]
            program, vao, vbo = cached_entry.program, cached_entry.vao, cached_entry.vbo

        # Efficient texture binding
        tex0.use(location=0)
        tex1.use(location=1)

        if "tex0" in program:
            program["tex0"] = 0
        if "tex1" in program:
            program["tex1"] = 1
        if "u_resolution" in program:
            program["u_resolution"] = (width, height)

        vao.render(moderngl.TRIANGLE_STRIP)
    finally:
        fbo.release()

    return out_tex
