import argparse
import sys
import time
import numpy as np
import moderngl
import glfw
from pathlib import Path

# --- Module import ---
from modules.ryoji_grid import RyojiGrid, RyojiGridParams

SHADER_PATH = Path("shaders/ryoji-grid.frag")

# --- Window and OpenGL setup ---
def create_window(width: int, height: int, title: str = "Oblique MVP"):
    if not glfw.init():
        raise RuntimeError("Failed to initialize GLFW")
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    window = glfw.create_window(width, height, title, None, None)
    if not window:
        glfw.terminate()
        raise RuntimeError("Failed to create GLFW window")
    glfw.make_context_current(window)
    return window

# --- Shader loading ---
def load_shader_source(path: Path) -> str:
    with open(path, 'r') as f:
        return f.read()

# --- Main ---
def main():
    parser = argparse.ArgumentParser(description="Oblique MVP - Minimal AV Synthesizer")
    parser.add_argument('--width', type=int, default=800, help='Window width')
    parser.add_argument('--height', type=int, default=600, help='Window height')
    args = parser.parse_args()

    width, height = args.width, args.height
    window = create_window(width, height)
    ctx = moderngl.create_context()

    # Fullscreen quad
    vertices = np.array([
        -1.0, -1.0, 0.0, 0.0,
         1.0, -1.0, 1.0, 0.0,
        -1.0,  1.0, 0.0, 1.0,
         1.0,  1.0, 1.0, 1.0,
    ], dtype='f4')
    vbo = ctx.buffer(vertices.tobytes())
    vao = ctx.simple_vertex_array(
        ctx.program(
            vertex_shader='''
                #version 330
                in vec2 in_vert;
                in vec2 in_uv;
                out vec2 v_uv;
                void main() {
                    v_uv = in_uv;
                    gl_Position = vec4(in_vert, 0.0, 1.0);
                }
            ''',
            fragment_shader=load_shader_source(SHADER_PATH),
        ),
        vbo,
        'in_vert', 'in_uv'
    )

    # Get uniforms
    prog = vao.program
    u_time = prog['u_time']
    u_resolution = prog['u_resolution']

    # Initialize the grid module (not used for logic yet)
    grid = RyojiGrid(RyojiGridParams(width=width, height=height))

    start_time = time.time()
    while not glfw.window_should_close(window):
        now = time.time()
        t = now - start_time
        ctx.clear(1.0, 1.0, 1.0, 1.0)
        prog['u_time'] = t
        prog['u_resolution'] = (width, height)
        vao.render(moderngl.TRIANGLE_STRIP)
        glfw.swap_buffers(window)
        glfw.poll_events()
    glfw.terminate()

if __name__ == "__main__":
    main() 