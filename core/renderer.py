import moderngl
import numpy as np
from typing import Any

_shader_cache = {}


def render_fullscreen_quad(ctx: moderngl.Context, frag_shader_path: str, uniforms: dict[str, Any]) -> None:
    """
    Render a fullscreen quad using the given fragment shader and uniforms.
    Caches the program, VAO, and VBO for efficiency.
    """
    global _shader_cache
    if frag_shader_path not in _shader_cache:
        with open(frag_shader_path, 'r') as f:
            fragment_shader = f.read()
        vertex_shader = '''
            #version 330
            in vec2 in_vert;
            in vec2 in_uv;
            out vec2 v_uv;
            void main() {
                v_uv = in_uv;
                gl_Position = vec4(in_vert, 0.0, 1.0);
            }
        '''
        program = ctx.program(
            vertex_shader=vertex_shader,
            fragment_shader=fragment_shader,
        )
        vertices = np.array([
            -1.0, -1.0, 0.0, 0.0,
             1.0, -1.0, 1.0, 0.0,
            -1.0,  1.0, 0.0, 1.0,
             1.0,  1.0, 1.0, 1.0,
        ], dtype='f4')
        vbo = ctx.buffer(vertices.tobytes())
        vao = ctx.simple_vertex_array(
            program,
            vbo,
            'in_vert', 'in_uv'
        )
        _shader_cache[frag_shader_path] = (program, vao)
    else:
        program, vao = _shader_cache[frag_shader_path]
    # Set uniforms
    texture_unit = 0
    for name, value in uniforms.items():
        if name in program:
            if isinstance(value, moderngl.Texture):
                value.use(location=texture_unit)
                # print(f"Binding texture uniform {name} to unit {texture_unit}")
                program[name] = texture_unit
                texture_unit += 1
            else:
                # print(f"Setting uniform {name} to {value}")
                program[name] = value
    vao.render(moderngl.TRIANGLE_STRIP) 


def render_to_texture(ctx: moderngl.Context, width: int, height: int, frag_shader_path: str, uniforms: dict[str, Any]) -> moderngl.Texture:
    """
    Render a fullscreen quad to an offscreen texture using the given fragment shader and uniforms.
    Returns the resulting texture.
    """
    tex = ctx.texture((width, height), 4)
    fbo = ctx.framebuffer(color_attachments=[tex])
    fbo.use()
    ctx.clear(0.0, 0.0, 0.0, 1.0)
    render_fullscreen_quad(ctx, frag_shader_path, uniforms)
    fbo.release()
    return tex


def blend_textures(ctx: moderngl.Context, width: int, height: int, tex0: moderngl.Texture, tex1: moderngl.Texture, blend_shader_path: str) -> moderngl.Texture:
    """
    Blend two textures using the specified blend shader and return the result as a new texture.
    """
    out_tex = ctx.texture((width, height), 4)
    fbo = ctx.framebuffer(color_attachments=[out_tex])
    fbo.use()
    ctx.clear(0.0, 0.0, 0.0, 1.0)
    global _shader_cache
    if blend_shader_path not in _shader_cache:
        with open(blend_shader_path, 'r') as f:
            fragment_shader = f.read()
        vertex_shader = '''
            #version 330
            in vec2 in_vert;
            in vec2 in_uv;
            out vec2 v_uv;
            void main() {
                v_uv = in_uv;
                gl_Position = vec4(in_vert, 0.0, 1.0);
            }
        '''
        program = ctx.program(
            vertex_shader=vertex_shader,
            fragment_shader=fragment_shader,
        )
        vertices = np.array([
            -1.0, -1.0, 0.0, 0.0,
             1.0, -1.0, 1.0, 0.0,
            -1.0,  1.0, 0.0, 1.0,
             1.0,  1.0, 1.0, 1.0,
        ], dtype='f4')
        vbo = ctx.buffer(vertices.tobytes())
        vao = ctx.simple_vertex_array(
            program,
            vbo,
            'in_vert', 'in_uv'
        )
        _shader_cache[blend_shader_path] = (program, vao)
    else:
        program, vao = _shader_cache[blend_shader_path]
    tex0.use(location=0)
    tex1.use(location=1)
    if 'tex0' in program:
        program['tex0'] = 0
    if 'tex1' in program:
        program['tex1'] = 1
    if 'u_resolution' in program:
        program['u_resolution'] = (width, height)
    vao.render(moderngl.TRIANGLE_STRIP)
    fbo.release()
    return out_tex 