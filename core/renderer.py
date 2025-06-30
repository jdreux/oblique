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
    for name, value in uniforms.items():
        if name in program:
            program[name] = value
    vao.render(moderngl.TRIANGLE_STRIP) 