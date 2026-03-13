"""Interactive REPL runner for Oblique patches.

This utility starts an :class:`~core.oblique_engine.ObliqueEngine` on the main
thread and drops the user into a Python REPL in a background thread.  The active
engine instance, a ``reload_patch`` helper, and live-coding helpers (``controls``,
``slider``, ``midi_map``, ``midi_learn``, ``set_scene``, ``store``) are all
exposed in the console's local scope.
"""

import argparse
import code
import importlib
import sys
import threading
import time
from pathlib import Path

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
    parser.add_argument(
        "--hot-reload-shaders",
        action="store_true",
        help="Reload GLSL shaders when files change",
    )
    parser.add_argument(
        "--hot-reload-python",
        action="store_true",
        help="Reload the patch module automatically when files change",
    )
    parser.add_argument(
        "--controls",
        action="store_true",
        help="Open a control surface window with parameter sliders and telemetry",
    )
    parser.add_argument("--log-level", type=str, default="INFO",
                        choices=["FATAL", "ERROR", "WARNING", "INFO", "DEBUG", "TRACE"],
                        help="Logging level")
    parser.add_argument("--log-file", type=str, default=None, help="Optional log file path")

    args = parser.parse_args()

    configure_logging(level=args.log_level, log_to_file=args.log_file is not None, log_file_path=args.log_file)

    # -- Live control infrastructure ------------------------------------------
    # Set up *before* loading the patch so helpers are available at module scope.
    import builtins

    from core.live_helpers import (
        make_controls_fn,
        make_midi_learn_fn,
        make_midi_map_fn,
        make_set_scene_fn,
        make_slider_fn,
    )
    from core.midi_mapper import MidiMapper
    from core.param_store import ParamStore

    store = ParamStore()
    midi_mapper = MidiMapper(store)
    control_window = None

    # Inject helpers into builtins so patch files can call controls() etc.
    # These are no-ops until --controls is passed (control_window=None).
    controls_fn = make_controls_fn(store, control_window)
    slider_fn = make_slider_fn(store, control_window)
    midi_learn_fn = make_midi_learn_fn(midi_mapper)
    midi_map_fn = make_midi_map_fn(midi_mapper)

    setattr(builtins, "controls", controls_fn)
    setattr(builtins, "slider", slider_fn)
    setattr(builtins, "midi_learn", midi_learn_fn)
    setattr(builtins, "midi_map", midi_map_fn)
    setattr(builtins, "store", store)

    try:
        patch = _load_patch(args.patch_path, args.patch_function, args.width, args.height)
    except Exception as exc:  # pragma: no cover - defensive logging
        error(f"Failed to load patch: {exc}")
        raise

    module_file = None
    module_obj = sys.modules.get(args.patch_path)
    if module_obj is not None:
        module_path_attr = getattr(module_obj, "__file__", None)
        if module_path_attr is not None:
            module_file = Path(module_path_attr).resolve()

    engine = ObliqueEngine(
        patch=patch,
        width=args.width,
        height=args.height,
        target_fps=args.fps,
        hot_reload_shaders=args.hot_reload_shaders,
    )

    if args.controls:
        info(
            "--controls is no longer supported in 'oblique start repl'. "
            "Use 'oblique live' instead for the TUI control surface."
        )

    set_scene_fn = make_set_scene_fn([engine])

    # Store REPL state for communication between threads
    repl_state = {
        'reload_requested': False,
        'quit_requested': False
    }

    python_watcher_stop = threading.Event()
    python_watcher_thread = None

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

        extra = ""
        if args.controls:
            extra = (
                "  controls(mod)      — auto-generate sliders for a module\n"
                "  slider(name, ...)  — create a standalone slider\n"
                "  midi_learn(key)    — arm MIDI learn for a param\n"
                "  midi_map(cc, key)  — bind CC number to a param\n"
                "  set_scene(mod)     — hot-swap the active scene\n"
                "  store              — direct ParamStore access\n"
            )

        banner = (
            "Oblique REPL.\n"
            "  r() / reload_patch() — reload patch\n"
            "  quit()               — exit\n"
            "  engine               — running engine instance\n"
            + extra
        )
        console_locals = {
            "engine": engine,
            "reload_patch": reload_patch,
            "r": reload_patch,
            "quit": quit_repl,
            "controls": controls_fn,
            "slider": slider_fn,
            "midi_learn": midi_learn_fn,
            "midi_map": midi_map_fn,
            "set_scene": set_scene_fn,
            "store": store,
            "midi_mapper": midi_mapper,
        }

        # Create a custom console that flushes output
        class FlushingConsole(code.InteractiveConsole):
            def write(self, data):
                sys.stdout.write(data)
                sys.stdout.flush()

        FlushingConsole(console_locals).interact(banner=banner)

    repl_thread = threading.Thread(target=start_repl, daemon=True)
    repl_thread.start()

    if args.hot_reload_python:
        if module_file is None or not module_file.exists():
            info(
                "Python hot reload requested but patch file could not be resolved; disabling automatic reload.",
            )
        else:
            info(f"Watching {module_file} for Python changes")

            def watch_python_patch() -> None:
                try:
                    last_mtime = module_file.stat().st_mtime
                except FileNotFoundError:
                    last_mtime = 0.0
                while not python_watcher_stop.wait(0.5):
                    try:
                        current_mtime = module_file.stat().st_mtime
                    except FileNotFoundError:
                        continue

                    if current_mtime <= last_mtime:
                        continue

                    last_mtime = current_mtime
                    repl_state['reload_requested'] = True
                    info("Patch file change detected; reload queued")

            python_watcher_thread = threading.Thread(
                target=watch_python_patch,
                daemon=True,
            )
            python_watcher_thread.start()

    # Start control window if requested (before entering render loop)
    if control_window is not None:
        control_window.start()
        info("Control surface window started")

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

            # Poll MIDI mapper
            midi_mapper.poll()

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
        if control_window is not None:
            control_window.stop()
        python_watcher_stop.set()
        if python_watcher_thread is not None:
            python_watcher_thread.join(timeout=1.0)
        engine.cleanup()


if __name__ == "__main__":
    main()
