"""Entry point for ``oblique live`` — TUI control surface + file watching.

Runs the GLFW render window on the main thread and spawns a Textual TUI
in a subprocess for parameter sliders, telemetry, and log output.
"""

from __future__ import annotations

import argparse
import importlib
import sys
import threading
import time
from pathlib import Path

from core.logger import configure_logging, error, info, set_log_sink
from core.oblique_engine import ObliqueEngine


def _load_patch(module_name: str, func_name: str, width: int, height: int):
    module = importlib.import_module(module_name)
    factory = getattr(module, func_name)
    return factory(width, height)


def main() -> None:
    parser = argparse.ArgumentParser(description="Oblique live mode")
    parser.add_argument("patch_path", help="Patch module path")
    parser.add_argument("patch_function", help="Patch factory function name")
    parser.add_argument("--width", type=int, default=800)
    parser.add_argument("--height", type=int, default=600)
    parser.add_argument("--fps", type=int, default=60)
    parser.add_argument("--hot-reload-shaders", action="store_true", default=True)
    parser.add_argument("--no-hot-reload-shaders", dest="hot_reload_shaders", action="store_false")
    parser.add_argument("--hot-reload-python", action="store_true", default=True)
    parser.add_argument("--no-hot-reload-python", dest="hot_reload_python", action="store_false")
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--log-file", default=None)

    args = parser.parse_args()

    configure_logging(
        level=args.log_level,
        log_to_file=args.log_file is not None,
        log_file_path=args.log_file,
        log_to_console=False,  # TUI owns the terminal
    )

    # -- Live control infrastructure ------------------------------------------
    from core.control_subprocess import spawn_control_tui
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

    # Spawn TUI subprocess (must happen before stdout is redirected)
    bridge, tui_process = spawn_control_tui(store)

    # Wire on_change so MIDI/code param changes forward to TUI
    store._on_change = bridge.send_param_update

    # Forward log messages to TUI
    set_log_sink(bridge.send_log)

    # Build helpers and wire them into the importable live_api module
    controls_fn = make_controls_fn(store, bridge)
    slider_fn = make_slider_fn(store, bridge)
    midi_learn_fn = make_midi_learn_fn(midi_mapper)
    midi_map_fn = make_midi_map_fn(midi_mapper)

    from core.live_api import _wire as _wire_live_api
    _wire_live_api(store, controls_fn, slider_fn, midi_learn_fn, midi_map_fn)

    # Load patch
    try:
        patch = _load_patch(args.patch_path, args.patch_function, args.width, args.height)
    except Exception as exc:
        error(f"Failed to load patch: {exc}")
        bridge.send_log("ERROR", f"Failed to load patch: {exc}")
        bridge.close()
        tui_process.terminate()
        raise

    # TUI owns the terminal — silence the parent's stdout/stderr so stray
    # prints from patches or libraries don't corrupt the TUI.
    # This is done AFTER patch loading so that load errors are visible.
    import os
    _devnull = open(os.devnull, "w")
    sys.stdout = _devnull
    sys.stderr = _devnull

    module_file = None
    module_obj = sys.modules.get(args.patch_path)
    if module_obj is not None:
        module_path_attr = getattr(module_obj, "__file__", None)
        if module_path_attr is not None:
            module_file = Path(module_path_attr).resolve()

    # Create engine
    engine = ObliqueEngine(
        patch=patch,
        width=args.width,
        height=args.height,
        target_fps=args.fps,
        hot_reload_shaders=args.hot_reload_shaders,
    )

    make_set_scene_fn([engine])

    # Send initial status to TUI
    bridge.send_status({
        "patch": args.patch_path,
        "shaders": args.hot_reload_shaders,
        "python": args.hot_reload_python,
    })

    # Send initial params snapshot
    bridge.send_params_snapshot()

    # -- File watchers --------------------------------------------------------
    python_watcher_stop = threading.Event()
    python_watcher_thread = None

    if args.hot_reload_python and module_file is not None and module_file.exists():
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
                reload_state["requested"] = True
                info("Patch file change detected; reload queued")

        python_watcher_thread = threading.Thread(target=watch_python_patch, daemon=True)
        python_watcher_thread.start()

    reload_state = {"requested": False}

    # -- Main render loop -----------------------------------------------------
    try:
        engine._create_window()
        engine.start_time = time.time()
        engine.running = True

        info(f"Starting Oblique live mode with patch {args.patch_path}")

        if engine.audio_output is not None:
            engine.audio_output.start()
            engine.audio_thread = threading.Thread(
                target=engine._audio_stream_playback,
                args=(engine.audio_output,),
                daemon=True,
            )
            engine.audio_thread.start()

        import glfw

        while not glfw.window_should_close(engine.window):
            # Poll IPC from TUI
            signal = bridge.poll_incoming()
            if signal == "quit":
                break
            if signal == "reload":
                reload_state["requested"] = True

            # Handle reload
            if reload_state["requested"]:
                reload_state["requested"] = False
                try:
                    module = importlib.import_module(args.patch_path)
                    importlib.reload(module)
                    engine.patch = _load_patch(
                        args.patch_path, args.patch_function, args.width, args.height
                    )
                    info("Patch reloaded successfully")
                    bridge.send_params_snapshot()
                except Exception as e:
                    error(f"Failed to reload patch: {e}")

            # Performance monitoring
            if engine.performance_monitor:
                engine.performance_monitor.begin_frame()

            frame_start = time.time()
            t = frame_start - engine.start_time

            # Poll MIDI
            midi_mapper.poll()

            # Render
            engine._render_patch(t, engine.patch)

            # Performance monitoring + telemetry
            if engine.performance_monitor:
                engine.performance_monitor.end_frame()

            stats = engine.get_performance_stats() or {}
            stats["memory"] = engine.performance_monitor.get_memory_usage_mb()
            bridge.send_telemetry(stats)

            # Frame rate limiting
            elapsed = time.time() - frame_start
            sleep_time = engine.frame_duration - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    except Exception as e:
        error(f"Error in Oblique live engine: {e}")
        raise
    finally:
        set_log_sink(None)
        python_watcher_stop.set()
        if python_watcher_thread is not None:
            python_watcher_thread.join(timeout=1.0)
        bridge.close()
        if tui_process.is_alive():
            tui_process.terminate()
            tui_process.join(timeout=2.0)
        engine.cleanup()


if __name__ == "__main__":
    main()
