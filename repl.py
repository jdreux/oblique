"""Interactive REPL runner for Oblique patches.

This utility starts an :class:`~core.oblique_engine.ObliqueEngine` in a background
thread and drops the user into a Python REPL. The active engine instance and a
``reload_patch`` helper are exposed in the console's local scope so patches can
be edited and reloaded on the fly. Shader hot reloading can be toggled via the
``--hot-reload-shaders`` flag.
"""

import argparse
import code
import importlib
import sys
import threading
import time

from core.logger import configure_logging, error, info
from core.oblique_engine import ObliqueEngine


def _load_patch(module_name: str, func_name: str, width: int, height: int):
    """Import a patch factory and instantiate an :class:`ObliquePatch`."""

    module = importlib.import_module(module_name)
    factory = getattr(module, func_name)
    return factory(width, height)


def main() -> None:
    parser = argparse.ArgumentParser(description="Oblique patch REPL")
    parser.add_argument("patch_path", help="Patch module path, e.g. projects.demo.shader_test")
    parser.add_argument("patch_function", help="Patch factory function name")
    parser.add_argument("--width", type=int, default=800)
    parser.add_argument("--height", type=int, default=600)
    parser.add_argument("--fps", type=int, default=60, help="Target frame rate")
    parser.add_argument("--hot-reload-shaders", action="store_true", default=True)
    parser.add_argument("--log-level", type=str, default="INFO",
                        choices=["FATAL", "ERROR", "WARNING", "INFO", "DEBUG", "TRACE"],
                        help="Logging level")
    parser.add_argument("--log-file", type=str, default=None, help="Optional log file path")

    args = parser.parse_args()

    configure_logging(level=args.log_level, log_to_file=args.log_file is not None, log_file_path=args.log_file)

    try:
        patch = _load_patch(args.patch_path, args.patch_function, args.width, args.height)
    except Exception as exc:  # pragma: no cover - defensive logging
        error(f"Failed to load patch: {exc}")
        raise

    engine = ObliqueEngine(
        patch=patch,
        width=args.width,
        height=args.height,
        target_fps=args.fps,
        hot_reload_shaders=args.hot_reload_shaders,
    )

    # Store REPL state for communication between threads
    repl_state = {
        'reload_requested': False,
        'quit_requested': False
    }

    def reload_patch() -> None:
        """Request patch reload - will be handled in main loop."""
        repl_state['reload_requested'] = True
        info("Patch reload requested")

    def quit_repl() -> None:
        """Request REPL quit - will be handled in main loop."""
        repl_state['quit_requested'] = True
        info("Quit requested")

    # Start REPL in background thread
    def start_repl():
        import sys
        import time
        
        # Give the engine a moment to start and show initial logs
        time.sleep(0.5)
        
        banner = (
            "Oblique REPL.\n"
            "Type reload_patch() or r() to reload patch, quit() to exit.\n"
            "The running engine is available as 'engine'.\n"
            "Engine logs will continue to appear above your input."
        )
        console_locals = {
            "engine": engine, 
            "reload_patch": reload_patch, 
            "r": reload_patch,
            "quit": quit_repl
        }
        
        # Create a custom console that flushes output
        class FlushingConsole(code.InteractiveConsole):
            def write(self, data):
                sys.stdout.write(data)
                sys.stdout.flush()
        
        FlushingConsole(console_locals).interact(banner=banner)

    repl_thread = threading.Thread(target=start_repl, daemon=True)
    repl_thread.start()

    # Run engine with REPL integration (must be on main thread for macOS)
    try:
        # Initialize engine
        engine._create_window()
        engine.start_time = time.time()
        engine.running = True
        
        info(f"Starting Oblique REPL engine with patch {engine.patch}")
        info("REPL is starting in background - you can type commands once you see the >>> prompt")
        
        if engine.hot_reload_shaders:
            info("Hot shader reload enabled")
            
        if engine.audio_output is not None:
            engine.audio_output.start()
            engine.audio_thread = threading.Thread(
                target=engine._audio_stream_playback,
                args=(engine.audio_output,),
                daemon=True,
            )
            engine.audio_thread.start()
        
        # Main render loop (on main thread)
        import glfw
        while not glfw.window_should_close(engine.window) and not repl_state['quit_requested']:
            # Handle reload requests
            if repl_state['reload_requested']:
                try:
                    print()  # Add newline before reload message
                    sys.stdout.flush()
                    module = importlib.import_module(args.patch_path)
                    importlib.reload(module)
                    engine.patch = _load_patch(args.patch_path, args.patch_function, args.width, args.height)
                    info("Patch reloaded successfully")
                    print(">>> ", end="")  # Restore prompt
                    sys.stdout.flush()
                except Exception as e:
                    error(f"Failed to reload patch: {e}")
                    print(">>> ", end="")  # Restore prompt even on error
                    sys.stdout.flush()
                repl_state['reload_requested'] = False
            
            # Performance monitoring
            if engine.performance_monitor:
                engine.performance_monitor.begin_frame()
            
            frame_start = time.time()
            t = frame_start - engine.start_time
            
            # Render modules
            engine._render_patch(t, engine.patch)
            
            # Performance monitoring
            if engine.performance_monitor:
                engine.performance_monitor.end_frame()
                engine.performance_monitor.print_stats(every_n_frames=60)
            
            # Frame rate limiting
            frame_end = time.time()
            elapsed = frame_end - frame_start
            sleep_time = engine.frame_duration - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
                
    except Exception as e:
        error(f"Error in Oblique REPL engine: {e}")
        raise
    finally:
        engine.cleanup()


if __name__ == "__main__":
    main()

