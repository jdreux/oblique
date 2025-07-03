import argparse
import time
import moderngl
import glfw  # type: ignore
from pathlib import Path
from typing import Union
import threading
import sounddevice as sd
import soundfile as sf
import numpy as np

# --- Module import ---
from modules.ryoji_grid import RyojiGrid, RyojiGridParams
from modules.pauric_particles import PauricParticles, PauricParticlesParams
from modules.circle_echo import CircleEcho, CircleEchoParams
from core.renderer import render_fullscreen_quad, render_to_texture, blend_textures
from inputs.audio_device_input import AudioDeviceInput  # Add this import
from processing.normalized_amplitude import NormalizedAmplitudeOperator
from modules.debug import DebugModule, DebugParams

SHADER_PATH = Path("shaders/ryoji-grid.frag")
ADDITIVE_BLEND_SHADER = "shaders/additive-blend.frag"

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

def audio_stream_playback(audio_input: 'AudioDeviceInput') -> None:
    """
    Streams audio from AudioDeviceInput in real-time using sounddevice.
    """
    if audio_input is None:
        return
    samplerate = audio_input.samplerate
    channels = audio_input.channels
    chunk_size = audio_input.chunk_size
    try:
        with sd.OutputStream(samplerate=samplerate, channels=channels, dtype='float32') as stream:
            while True:
                chunk = audio_input.read()
                if chunk.shape[0] == 0:
                    break  # End of file
                stream.write(chunk.astype('float32'))
    except Exception as e:
        print(f"[AUDIO ERROR] {e}")

# --- Main ---
def main():
    parser = argparse.ArgumentParser(description="Oblique MVP - Minimal AV Synthesizer")
    parser.add_argument('--width', type=int, default=800, help='Window width')
    parser.add_argument('--height', type=int, default=600, help='Window height')
    parser.add_argument('--audio', type=str, default=None, help='Path to audio file for playback')
    # parser.add_argument('--module', type=str, default='pauric', choices=['pauric', 'ryoji'], help='AV module to run (pauric or ryoji)')
    args = parser.parse_args()

    width, height = args.width, args.height
    window = create_window(width, height)
    ctx = moderngl.create_context()

    # --- Audio input setup ---
    audio_input = None
    audio_thread = None
    amplitude_processor = NormalizedAmplitudeOperator()
    amplitude = 0.0
    if args.audio:
        audio_input = AudioDeviceInput(args.audio)
        audio_input.start()
        audio_thread = threading.Thread(target=audio_stream_playback, args=(audio_input,), daemon=True)
        audio_thread.start()
    

    # --- Debug module setup ---
    debug_params = DebugParams(width=width, height=height, number=0.0, text="Debug")
    debug_module = DebugModule(debug_params)
    # --- Hardcoded module list (order matters) ---
    modules = [
        # PauricParticles(PauricParticlesParams(width=width, height=height)),
        # RyojiGrid(RyojiGridParams(width=width, height=height)),
        CircleEcho(CircleEchoParams(width=width, height=height)),
        debug_module,
    ]

    # Get the framebuffer size to account for Retina display scaling
    fb_width, fb_height = ctx.screen.size

    FRAME_DURATION = 1.0 / 60.0  # 60 Hz = 16.67 ms per frame
    start_time = time.time()
    last_frame_time = start_time

    while not glfw.window_should_close(window):
        frame_start = time.time()
        t = frame_start - start_time
        ctx.viewport = (0, 0, width, height)
        ctx.clear(1.0, 1.0, 1.0, 1.0)

        # --- Audio input and amplitude processing ---
        if audio_input is not None and amplitude_processor is not None:
            try:
                chunk = audio_input.peek()
                if chunk is not None:
                    amplitude = amplitude_processor.process(chunk)
            except Exception as e:
                amplitude = 0.0

        # --- Update DebugModule with amplitude ---
        print(f"Amplitude: {amplitude}")
        debug_module.update(DebugParams(width=width, height=height, number=amplitude, text=f"Amp: {amplitude:.3f}"))

        # Render each module to a texture
        textures = []
        for module in modules:
            # module.update(module.params)  # Use default params for now
            render_data = module.render(t)
            tex = render_to_texture(ctx, fb_width, fb_height, render_data['frag_shader_path'], render_data['uniforms'])
            textures.append(tex)
        # Blend all textures in order (additive)
        if len(textures) == 1:
            final_tex = textures[0]
        else:
            final_tex = textures[0]
            for tex in textures[1:]:
                final_tex = blend_textures(ctx, fb_width, fb_height, final_tex, tex, ADDITIVE_BLEND_SHADER)
        ctx.viewport = (0, 0, fb_width, fb_height)
        # Display final texture to screen
        render_fullscreen_quad(
            ctx,
            "shaders/passthrough.frag",  # Generic shader that simply displays a texture
            {
                'tex0': final_tex,  # The final composited texture
                'u_time': t,
                'u_resolution': (fb_width, fb_height),
            }
        )
        final_tex.use(location=0)
        glfw.swap_buffers(window)
        glfw.poll_events()

        # --- 60 Hz frame limiting ---
        frame_end = time.time()
        elapsed = frame_end - frame_start
        sleep_time = FRAME_DURATION - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)
        else:
            print(f"[WARNING] Frame took too long: {elapsed:.4f}s (target: {FRAME_DURATION:.4f}s)")

    glfw.terminate()
    if audio_input is not None:
        audio_input.stop()

if __name__ == "__main__":
    main() 