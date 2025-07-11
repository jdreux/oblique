import time
import threading
import moderngl
import glfw  # type: ignore
import sounddevice as sd
import numpy as np
from typing import Optional, List, Dict
from pathlib import Path

from core.oblique_patch import ObliquePatch
from core.renderer import render_fullscreen_quad, blend_textures
from core.performance_monitor import PerformanceMonitor
from inputs.audio_device_input import AudioDeviceInput
from inputs.base_input import BaseInput
from processing.normalized_amplitude import NormalizedAmplitudeOperator


class ObliqueEngine:
    """
    Main engine for running Oblique patches with audio playback and video rendering.
    Handles the complete audio-visual pipeline from patch execution to screen output.
    """

    def __init__(
        self,
        patch: ObliquePatch,
        width: int = 800,
        height: int = 600,
        title: str = "Oblique MVP",
        target_fps: int = 60,
        debug: bool = False,
        monitor: Optional[int] = None,
    ):
        """
        Initialize the Oblique engine with a patch and display settings.

        Args:
            patch: The ObliquePatch containing modules and inputs
            width: Window width in pixels
            height: Window height in pixels
            title: Window title
            target_fps: Target frame rate for rendering
            debug: Enable debug mode with performance monitoring
            monitor: Monitor index to open window on (None for default)
        """
        self.patch = patch
        self.width = width
        self.height = height
        self.title = title
        self.target_fps = target_fps
        self.frame_duration = 1.0 / target_fps
        self.debug = debug
        self.monitor = monitor
        # Set global debug mode for shader reloading
        from core.renderer import set_debug_mode

        set_debug_mode(debug)

        # Performance monitoring
        self.performance_monitor = PerformanceMonitor() if debug else None

        # OpenGL context
        self.window: Optional[glfw._GLFWwindow] = None
        self.ctx: Optional[moderngl.Context] = None

        # Audio handling
        self.audio_input: Optional[BaseInput] = None
        self.audio_thread: Optional[threading.Thread] = None

        self.audio_input = patch.get_audio_input()

        # Timing
        self.start_time = 0.0
        self.running = False

        # Shader paths
        self.additive_blend_shader = "shaders/additive-blend.frag"
        self.passthrough_shader = "shaders/passthrough.frag"

    def _create_window(self) -> None:
        """Create and configure the GLFW window."""
        if not glfw.init():
            raise RuntimeError("Failed to initialize GLFW")

        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)

        # Create windowed window (not fullscreen)
        self.window = glfw.create_window(
            self.width, self.height, self.title, None, None
        )
        if not self.window:
            glfw.terminate()
            raise RuntimeError("Failed to create GLFW window")

        # Position window on specified monitor if requested
        if self.monitor is not None:
            monitors = glfw.get_monitors()
            if 0 <= self.monitor < len(monitors):
                monitor_obj = monitors[self.monitor]
                # Get monitor position and work area
                monitor_pos = glfw.get_monitor_pos(monitor_obj)
                work_area = glfw.get_monitor_workarea(monitor_obj)

                # Center the window on the monitor
                x = monitor_pos[0] + (work_area[2] - self.width) // 2
                y = monitor_pos[1] + (work_area[3] - self.height) // 2

                glfw.set_window_pos(self.window, x, y)
                print(f"Positioned window on monitor {self.monitor} at ({x}, {y})")
            else:
                print(
                    f"Warning: Monitor {self.monitor} not found. Using default position."
                )
                print(f"Available monitors: {len(monitors)}")

        glfw.make_context_current(self.window)
        self.ctx = moderngl.create_context()

    @staticmethod
    def list_monitors() -> None:
        """List all available monitors and their information."""
        if not glfw.init():
            print("Failed to initialize GLFW")
            return

        monitors = glfw.get_monitors()
        print(f"Found {len(monitors)} monitor(s):")

        for i, monitor in enumerate(monitors):
            name = glfw.get_monitor_name(monitor)
            video_mode = glfw.get_video_mode(monitor)
            if video_mode:
                print(
                    f"  Monitor {i}: {name} ({video_mode.size[0]}x{video_mode.size[1]} @ {video_mode.refresh_rate}Hz)"
                )
            else:
                print(f"  Monitor {i}: {name} (no video mode available)")

        glfw.terminate()

    def _audio_stream_playback(self, audio_input: BaseInput) -> None:
        """
        Streams audio from AudioDeviceInput in real-time using sounddevice.
        Runs in a separate thread.
        """

        # Use standard audio defaults for real-time streaming
        samplerate = 44100  # Standard CD quality
        channels = 2  # Stereo

        try:
            with sd.OutputStream(
                samplerate=samplerate, channels=channels, dtype="float32"
            ) as stream:
                while self.running:
                    chunk = audio_input.read()
                    if chunk.shape[0] == 0:
                        break  # End of file
                    stream.write(chunk.astype("float32"))
        except Exception as e:
            print(f"[AUDIO ERROR] {e}")

    def _render_modules(self, t: float) -> moderngl.Texture:
        """
        Render all modules in the patch and blend them together.

        Args:
            t: Current time in seconds

        Returns:
            The final composited texture
        """
        if self.ctx is None:
            raise RuntimeError("OpenGL context not initialized")

        # Get framebuffer size to account for Retina display scaling
        fb_width, fb_height = self.ctx.screen.size

        # Render each module to a texture
        textures: List[moderngl.Texture] = []
        for module in self.patch.modules:
            tex = module.render_texture(self.ctx, fb_width, fb_height, t)
            textures.append(tex)

        # Blend all textures in order (additive)
        if len(textures) == 0:
            print("No textures to render")
            # Create a black texture if no modules
            tex = self.ctx.texture((fb_width, fb_height), 4, dtype="f1", alignment=1)
            tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
            tex.repeat_x = False
            tex.repeat_y = False
            return tex
        elif len(textures) == 1:
            return textures[0]
        else:
            final_tex = textures[0]
            for tex in textures[1:]:
                final_tex = blend_textures(
                    self.ctx,
                    fb_width,
                    fb_height,
                    final_tex,
                    tex,
                    self.additive_blend_shader,
                )
            return final_tex

    def _display_frame(self, final_tex: moderngl.Texture, t: float) -> None:
        """
        Display the final composited texture to the screen.

        Args:
            final_tex: The final composited texture
            t: Current time in seconds
        """
        if self.ctx is None:
            raise RuntimeError("OpenGL context not initialized")

        fb_width, fb_height = self.ctx.screen.size
        self.ctx.viewport = (0, 0, fb_width, fb_height)

        # Display final texture to screen
        render_fullscreen_quad(
            self.ctx,
            self.passthrough_shader,
            {
                "u_texture": final_tex,
                "u_time": t,
                "u_resolution": (fb_width, fb_height),
            },
        )
        final_tex.use(location=0)
        glfw.swap_buffers(self.window)

    def run(self) -> None:
        """
        Run the Oblique engine with the given patch.

        Args:
        """
        try:
            # Setup window and OpenGL context
            self._create_window()

            # Initialize timing
            self.start_time = time.time()
            self.running = True

            print(f"Starting Oblique engine with {len(self.patch.modules)} modules")

            if self.debug:
                print("Debug mode enabled - Performance monitoring active")

            if self.audio_input is not None:
                self.audio_input.start()
                self.audio_thread = threading.Thread(
                    target=self._audio_stream_playback,
                    args=(self.audio_input,),
                    daemon=True,
                )
                self.audio_thread.start()

            # Main render loop
            while not glfw.window_should_close(self.window):
                # Performance monitoring
                if self.performance_monitor:
                    self.performance_monitor.begin_frame()

                frame_start = time.time()
                t = frame_start - self.start_time

                # Clear the screen
                if self.ctx is None:
                    raise RuntimeError("OpenGL context not initialized")
                self.ctx.viewport = (0, 0, self.width, self.height)
                self.ctx.clear(1.0, 1.0, 1.0, 1.0)

                # Render modules
                final_tex = self._render_modules(t)

                # Display frame
                self._display_frame(final_tex, t)

                # Handle events
                glfw.poll_events()

                # Performance monitoring
                if self.performance_monitor:
                    self.performance_monitor.end_frame()
                    self.performance_monitor.print_stats(every_n_frames=60)

                # Frame rate limiting
                frame_end = time.time()
                elapsed = frame_end - frame_start
                sleep_time = self.frame_duration - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
                # else:
                #     if self.debug:
                #         print(f"[WARNING] Frame took too long: {elapsed:.4f}s (target: {self.frame_duration:.4f}s)")

        except Exception as e:
            print(f"Error in Oblique engine: {e}")
            raise
        finally:
            self.cleanup()

    def get_performance_stats(self) -> Optional[Dict[str, float]]:
        """
        Get current performance statistics if debug mode is enabled.

        Returns:
            Performance statistics dictionary or None if debug mode is disabled
        """
        if self.performance_monitor:
            return self.performance_monitor.get_stats()
        return None

    def cleanup(self) -> None:
        """Clean up resources."""
        self.running = False

        if self.audio_input is not None:
            self.audio_input.stop()

        if self.audio_thread is not None and self.audio_thread.is_alive():
            self.audio_thread.join(timeout=1.0)

        if self.window is not None:
            glfw.terminate()
