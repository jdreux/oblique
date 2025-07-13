import threading
import time
from typing import Dict, List, Optional

import glfw  # type: ignore
import moderngl
import sounddevice as sd

from core.oblique_patch import ObliquePatch
from core.performance_monitor import PerformanceMonitor
from core.renderer import blend_textures, render_fullscreen_quad
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

        samplerate = audio_input.sample_rate
        channels = audio_input.num_channels
        chunk_size = audio_input.chunk_size

        print(f"[AUDIO] Streaming audio from {audio_input.device_name} at {samplerate} Hz with {channels} channels, "
        f"chunk size: {chunk_size} samples ({chunk_size / samplerate * 1000:.1f}ms)")

        try:
            with sd.OutputStream(
                samplerate=samplerate,
                channels=channels,
                dtype="float32",
                blocksize=chunk_size,
                latency="low"  # Match input latency mode
            ) as stream:

                # Comprehensive timing diagnostics
                last_chunk_time = time.time()
                expected_interval = chunk_size / samplerate
                buffer_underruns = 0
                consecutive_underruns = 0
                chunks_processed = 0
                
                # Detailed timing tracking
                read_times = []
                write_times = []
                loop_times = []
                
                # Performance counters
                total_read_time = 0.0
                total_write_time = 0.0
                total_loop_time = 0.0
                max_read_time = 0.0
                max_write_time = 0.0
                max_loop_time = 0.0

                while self.running:
                    loop_start = time.time()
                    
                    try:
                        # Time the read operation
                        read_start = time.time()
                        chunk = audio_input.read()
                        read_end = time.time()
                        read_time = read_end - read_start
                        
                        read_times.append(read_time)
                        total_read_time += read_time
                        max_read_time = max(max_read_time, read_time)

                        # Check if we got a zero chunk (no audio data)
                        if chunk.shape[0] == 0:
                            break  # End of file

                        # Ensure chunk is the right shape and type
                        if chunk.shape[1] != channels:
                            # If we have more channels than expected, take the first ones
                            chunk = chunk[:, :channels]

                        # Time the write operation
                        write_start = time.time()
                        stream.write(chunk.astype("float32"))
                        write_end = time.time()
                        write_time = write_end - write_start
                        
                        write_times.append(write_time)
                        total_write_time += write_time
                        max_write_time = max(max_write_time, write_time)
                        
                        chunks_processed += 1
                        loop_end = time.time()
                        loop_time = loop_end - loop_start
                        
                        loop_times.append(loop_time)
                        total_loop_time += loop_time
                        max_loop_time = max(max_loop_time, loop_time)

                        # Detailed logging every 50 chunks
                        if chunks_processed % 50 == 0:
                            avg_read = total_read_time / chunks_processed
                            avg_write = total_write_time / chunks_processed
                            avg_loop = total_loop_time / chunks_processed
                            
                            # Get queue status for diagnostics
                            queue_status = audio_input.get_queue_status()
                            
                            print(f"[AUDIO] Chunk {chunks_processed}: "
                                  f"read={read_time*1000:.1f}ms (avg={avg_read*1000:.1f}ms, max={max_read_time*1000:.1f}ms), "
                                  f"write={write_time*1000:.1f}ms (avg={avg_write*1000:.1f}ms, max={max_write_time*1000:.1f}ms), "
                                  f"loop={loop_time*1000:.1f}ms (avg={avg_loop*1000:.1f}ms, max={max_loop_time*1000:.1f}ms), "
                                  f"queue={queue_status['queue_size']}/{queue_status['queue_maxsize']} "
                                  f"({'full' if queue_status['is_full'] else 'empty' if queue_status['is_empty'] else 'ok'})")

                        # Monitor timing for buffer underruns
                        current_time = time.time()
                        actual_interval = current_time - last_chunk_time
                        if actual_interval > expected_interval * 1.2:  # Allow some tolerance
                            buffer_underruns += 1
                            consecutive_underruns += 1
                            if consecutive_underruns >= 3:  # Log after 3 consecutive underruns
                                print(f"[AUDIO] Sustained buffer underruns detected (total: {buffer_underruns}). "
                                f"Last expected: {expected_interval*1000:.1f}ms, actual: {actual_interval*1000:.1f}ms")
                                consecutive_underruns = 0
                        else:
                            consecutive_underruns = 0

                        last_chunk_time = current_time

                    except Exception as e:
                        print(f"[AUDIO ERROR] Failed to process chunk: {e}")
                        # Small delay to prevent tight error loops
                        time.sleep(0.001)

                # Final statistics
                if chunks_processed > 0:
                    avg_read = total_read_time / chunks_processed
                    avg_write = total_write_time / chunks_processed
                    avg_loop = total_loop_time / chunks_processed
                    
                    print(f"\n[AUDIO] Final Statistics:")
                    print(f"  Total chunks processed: {chunks_processed}")
                    print(f"  Average read time: {avg_read*1000:.2f}ms")
                    print(f"  Average write time: {avg_write*1000:.2f}ms")
                    print(f"  Average loop time: {avg_loop*1000:.2f}ms")
                    print(f"  Max read time: {max_read_time*1000:.2f}ms")
                    print(f"  Max write time: {max_write_time*1000:.2f}ms")
                    print(f"  Max loop time: {max_loop_time*1000:.2f}ms")
                    print(f"  Buffer underruns: {buffer_underruns}")
                    
                    # Performance analysis
                    total_processing_time = avg_read + avg_write
                    available_time = expected_interval
                    utilization = (total_processing_time / available_time) * 100
                    
                    print(f"  Processing time: {total_processing_time*1000:.2f}ms")
                    print(f"  Available time: {available_time*1000:.2f}ms")
                    print(f"  CPU utilization: {utilization:.1f}%")
                    
                    if utilization > 80:
                        print(f"  [WARNING] High CPU utilization ({utilization:.1f}%). Consider larger chunk size.")
                    elif buffer_underruns > 0:
                        print(f"  [WARNING] Buffer underruns detected. Consider larger chunk size.")
                    else:
                        print(f"  [OK] Performance looks good for this chunk size.")

        except Exception as e:
            print(f"[AUDIO ERROR] Stream setup failed: {e}")

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

        # Get framebuffer size to account for Retina display scaling
        fb_width, fb_height = self.ctx.screen.size

        # Render each module to a texture
        textures: List[moderngl.Texture] = []
        for module in self.patch.modules:
            tex = module.render_texture(self.ctx, fb_width, fb_height, t)
            textures.append(tex)


        final_tex = None

        if len(textures) == 0:
            print("No textures to render")
            # Create a black texture if no modules
            tex = self.ctx.texture((fb_width, fb_height), 4, dtype="f1", alignment=1)
            tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
            tex.repeat_x = False
            tex.repeat_y = False
            textures.append(tex)

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

        #release all textures
        for tex in textures:
            tex.release()


    def _display_frame(self, final_tex: moderngl.Texture, t: float) -> None:
        """
        Display the final composited texture to the screen.

        Args:
            final_tex: The final composited texture
            t: Current time in seconds
        """
        if self.ctx is None:
            raise RuntimeError("OpenGL context not initialized")

        fb_width, fb_height  = self.ctx.screen.size
        self.ctx.viewport = (0, 0, fb_width, fb_height)

        # Clear the screen
        self.ctx.clear(1.0, 1.0, 1.0, 1.0)

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

        # Clean up shader cache
        from core.renderer import cleanup_shader_cache
        cleanup_shader_cache()

        if self.window is not None:
            glfw.terminate()
