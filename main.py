import argparse
import time
import moderngl
import glfw  # type: ignore
from pathlib import Path

# --- Module import ---
from modules.ryoji_grid import RyojiGrid, RyojiGridParams
from core.renderer import render_fullscreen_quad

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

    # Initialize the grid module
    grid = RyojiGrid(RyojiGridParams(width=width, height=height))

    start_time = time.time()
    while not glfw.window_should_close(window):
        now = time.time()
        t = now - start_time
        ctx.clear(1.0, 1.0, 1.0, 1.0)
        grid.update(RyojiGridParams(width=width, height=height))
        render_data = grid.render(t)
        render_fullscreen_quad(ctx, render_data['frag_shader_path'], render_data['uniforms'])
        glfw.swap_buffers(window)
        glfw.poll_events()
    glfw.terminate()

if __name__ == "__main__":
    main() 