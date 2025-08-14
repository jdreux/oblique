
from typing import TYPE_CHECKING, Any

import moderngl
import numpy as np

from core.logger import error, warning
from core.shader_preprocessor import preprocess_shader

if TYPE_CHECKING:
    from modules.core.base_av_module import BaseAVModule, Uniforms

_shader_cache = {}
_texture_cache = {}
_debug_mode = False
_ctx = None

def set_debug_mode(debug: bool) -> None:
    """
    Set debug mode globally. When enabled, shaders are reloaded from file every time.

    Args:
        debug: If True, bypass shader cache and reload from file every time
    """
    global _debug_mode
    _debug_mode = debug

def set_ctx(ctx: moderngl.Context) -> None:
    """
    Set the context globally.
    """
    global _ctx
    _ctx = ctx

def cleanup_shader_cache() -> None:
    """
    Release all cached shader resources. Call this when shutting down the application.
    """
    global _shader_cache
    for entry in _shader_cache.values():
        _release_shader_cache_entry(entry)
    _shader_cache.clear()


def _release_shader_cache_entry(entry: tuple) -> None:
    """
    Safely release program, VAO, and VBO resources from a shader cache entry.
    """
    if entry is not None:
        program, vao, vbo = entry
        try:
            vao.release()
        except Exception:
            warning("Failed to release VAO")
            pass
        try:
            vbo.release()
        except Exception:
            warning("Failed to release VBO")
            pass
        try:
            program.release()
        except Exception:
            warning("Failed to release program")
            pass


def render_fullscreen_quad(
    ctx: moderngl.Context, frag_shader_path: str, uniforms: dict[str, Any]
) -> tuple[moderngl.Program, moderngl.VertexArray, moderngl.Buffer]:
    """
    Render a fullscreen quad using the given fragment shader and uniforms.
    Caches the program, VAO, and VBO for efficiency.
    Returns the program, vao, and vbo.
    """
    global _shader_cache, _debug_mode


    # In debug mode, always reload shader from file
    if _debug_mode and frag_shader_path in _shader_cache:
        _release_shader_cache_entry(_shader_cache[frag_shader_path])
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
        _shader_cache[frag_shader_path] = (program, vao, vbo)
    else:
        program, vao, vbo = _shader_cache[frag_shader_path]

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
    """
    Render a fullscreen quad to an offscreen texture using the given fragment shader and uniforms.
    The optional `cache_tag` allows distinct cache entries for different internal passes
    belonging to the same module class. This prevents cache collisions when a module
    renders several off-screen buffers of identical resolution.
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

        global _shader_cache, _debug_mode

        # In debug mode, always reload shader from file
        if _debug_mode and blend_shader_path in _shader_cache:
            _release_shader_cache_entry(_shader_cache[blend_shader_path])
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
            _shader_cache[blend_shader_path] = (program, vao, vbo)
        else:
            program, vao, vbo = _shader_cache[blend_shader_path]

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
