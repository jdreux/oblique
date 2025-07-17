import threading
import time
from typing import Dict, List, Optional

import glfw  # type: ignore
import moderngl
import sounddevice as sd

from core.logger import debug, error, info, warning
from core.oblique_patch import ObliquePatch
from core.performance_monitor import PerformanceMonitor
from core.renderer import blend_textures
from inputs.base_input import BaseInput


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

        # Cached display resources (created in _create_display_resources)
        self._display_program: Optional[moderngl.Program] = None
        self._display_vao: Optional[moderngl.VertexArray] = None
        self._display_vbo: Optional[moderngl.Buffer] = None

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

            info(f"Starting Oblique engine with {len(self.patch.modules)} modules")

            if self.debug:
                info("Debug mode enabled - Performance monitoring active")

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

                # Render modules
                self._render_modules(t)

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

        except Exception as e:
            error(f"Error in Oblique engine: {e}")
            raise
        finally:
            self.cleanup()



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
                info(f"Positioned window on monitor {self.monitor} at ({x}, {y})")
            else:
                warning(f"Monitor {self.monitor} not found. Using default position.")
                debug(f"Available monitors: {len(monitors)}")

        glfw.make_context_current(self.window)
        self.ctx = moderngl.create_context()

        # Set the context globally
        from core.renderer import set_ctx
        set_ctx(self.ctx)

        # Create cached display resources
        self._create_display_resources()

    def _create_display_resources(self) -> None:
        """Create and cache the display shader resources for efficient reuse."""
        if self.ctx is None:
            raise RuntimeError("OpenGL context not initialized")

        # Create the passthrough shader program once
        with open(self.passthrough_shader, "r") as f:
            fragment_shader = f.read()
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
        self._display_program = self.ctx.program(
            vertex_shader=vertex_shader,
            fragment_shader=fragment_shader,
        )

        # Create vertex data for fullscreen quad
        import numpy as np
        vertices = np.array(
            [
                -1.0, -1.0, 0.0, 0.0,
                1.0, -1.0, 1.0, 0.0,
                -1.0, 1.0, 0.0, 1.0,
                1.0, 1.0, 1.0, 1.0,
            ],
            dtype="f4",
        )
        self._display_vbo = self.ctx.buffer(vertices.tobytes())
        self._display_vao = self.ctx.simple_vertex_array(
            self._display_program,
            self._display_vbo,
            "in_vert",
            "in_uv"
        )

    @staticmethod
    def list_monitors() -> None:
        """List all available monitors and their information."""
        if not glfw.init():
            error("Failed to initialize GLFW")
            return

        monitors = glfw.get_monitors()
        info(f"Found {len(monitors)} monitor(s):")

        for i, monitor in enumerate(monitors):
            name = glfw.get_monitor_name(monitor)
            video_mode = glfw.get_video_mode(monitor)
            if video_mode:
                info(
                    f"  Monitor {i}: {name} ({video_mode.size[0]}x{video_mode.size[1]} @ {video_mode.refresh_rate}Hz)"
                )
            else:
                info(f"  Monitor {i}: {name} (no video mode available)")

        glfw.terminate()

    def _audio_stream_playback(self, audio_input: BaseInput) -> None:
        """
        Streams audio from AudioDeviceInput in real-time using sounddevice.
        Runs in a separate thread.
        """

        samplerate = audio_input.sample_rate
        channels = audio_input.num_channels
        chunk_size = audio_input.chunk_size

        info(f"[AUDIO] Streaming audio from {audio_input.device_name} at {samplerate} Hz with {channels} channels, "
        f"chunk size: {chunk_size} samples ({chunk_size / samplerate * 1000:.1f}ms)")

        try:
            with sd.OutputStream(
                samplerate=samplerate,
                channels=channels,
                dtype="float32",
                blocksize=chunk_size,
                latency="low"  # Match input latency mode
            ) as stream:

                # Timing monitoring for buffer underruns
                last_chunk_time = time.time()
                expected_interval = chunk_size / samplerate
                buffer_underruns = 0
                consecutive_underruns = 0
                chunks_processed = 0

                while self.running:
                    try:
                        chunk = audio_input.read()

                        # Check if we got a zero chunk (no audio data)
                        if chunk.shape[0] == 0:
                            break  # End of file

                        # Ensure chunk is the right shape and type
                        if chunk.shape[1] != channels:
                            # If we have more channels than expected, take the first ones
                            chunk = chunk[:, :channels]

                        # Write to stream with error handling
                        stream.write(chunk.astype("float32"))
                        chunks_processed += 1

                        # Monitor timing for buffer underruns
                        current_time = time.time()
                        actual_interval = current_time - last_chunk_time

                        # Log progress every 100 chunks
                        if chunks_processed % 100 == 0:
                            current_latency = actual_interval * 1000  # Convert to milliseconds
                            debug(f"[AUDIO] Processed {chunks_processed} chunks, latency: {current_latency:.1f}ms")
                        if actual_interval > expected_interval * 1.2:  # Allow some tolerance
                            buffer_underruns += 1
                            consecutive_underruns += 1
                            if consecutive_underruns >= 10:  # Log after 3 consecutive underruns
                                warning(f"[AUDIO] Sustained buffer underruns detected (total: {buffer_underruns}). "
                                f"Last expected: {expected_interval*1000:.1f}ms, actual: {actual_interval*1000:.1f}ms")
                                consecutive_underruns = 0
                        else:
                            consecutive_underruns = 0

                        last_chunk_time = current_time

                    except Exception as e:
                        error(f"[AUDIO ERROR] Failed to process chunk: {e}")
                        # Small delay to prevent tight error loops
                        time.sleep(0.001)

                info(f"[AUDIO] Playback loop ended. Processed {chunks_processed} chunks total.")

        except Exception as e:
            error(f"[AUDIO ERROR] Stream setup failed: {e}")

    def _render_modules(self, t: float):
        """
        Render all modules in the patch and blend them together.

        Args:
            t: Current time in seconds

        Returns:
            The final composited texture
        """
        if self.ctx is None:
            raise RuntimeError("OpenGL context not initialized")

        if len(self.patch.modules) == 0:
            warning("No modules to render")
            time.sleep(1/60) # Sleep for 1 frame
            return

        # Get framebuffer size to account for Retina display scaling
        fb_width, fb_height = self.ctx.screen.size

        # Render each module to a texture
        textures: List[moderngl.Texture] = []

        for module in self.patch.modules:
            tex = module.render_texture(self.ctx, fb_width, fb_height, t)
            textures.append(tex)

        final_tex = None

        # if len(textures) == 0:
        #     # warning("No textures to render")
        #     # Create a black texture if no modules
        #     tex = self.ctx.texture((fb_width, fb_height), 4, dtype="f1", alignment=1)
        #     tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
        #     tex.repeat_x = False
        #     tex.repeat_y = False
        #     textures = [tex]

        # Blend all textures in order (additive)
        if len(textures) == 1:
            final_tex = textures[0]
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

        # Display frame
        self._display_frame(final_tex, t)

        # Handle events
        glfw.poll_events()


    def _display_frame(self, final_tex: moderngl.Texture, t: float) -> None:
        """
        Display the final composited texture to the screen using cached resources.

        Args:
            final_tex: The final composited texture
            t: Current time in seconds
        """
        if self.ctx is None or self._display_program is None or self._display_vao is None:
            raise RuntimeError("OpenGL context or display resources not initialized")

        fb_width, fb_height = self.ctx.screen.size
        self.ctx.viewport = (0, 0, fb_width, fb_height)

        # Clear the screen
        self.ctx.clear(1.0, 1.0, 1.0, 1.0)

        # Bind texture to texture unit 0
        final_tex.use(location=0)


        # Render using cached VAO
        self._display_vao.render(moderngl.TRIANGLE_STRIP)

        # Swap buffers
        glfw.swap_buffers(self.window)



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

        # Clean up cached display resources
        if self._display_vao is not None:
            try:
                self._display_vao.release()
            except Exception:
                pass
        if self._display_vbo is not None:
            try:
                self._display_vbo.release()
            except Exception:
                pass
        if self._display_program is not None:
            try:
                self._display_program.release()
            except Exception:
                pass

        # Clean up shader cache
        from core.renderer import cleanup_shader_cache
        cleanup_shader_cache()

        if self.window is not None:
            glfw.terminate()
