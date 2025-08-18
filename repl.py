"""Interactive REPL runner for Oblique patches.

This utility starts an :class:`~core.oblique_engine.ObliqueEngine` in a background
thread and drops the user into a Python REPL. The active engine instance and a
``reload_patch`` helper are exposed in the console's local scope so patches can
be edited and reloaded on the fly. Shader hot reloading can be toggled via the
``--hot-reload-shaders`` flag.
"""

import argparse
import importlib
import threading
import code

from core import ObliqueEngine
from core.logger import configure_logging, info, error


def _load_patch(module_name: str, func_name: str, width: int, height: int):
    """Import a patch factory and instantiate an :class:`ObliquePatch`."""

    module = importlib.import_module(module_name)
    factory = getattr(module, func_name)
    return factory(width, height)


def main() -> None:
    parser = argparse.ArgumentParser(description="Oblique patch REPL")
    parser.add_argument("module", help="Patch module path, e.g. projects.demo.shader_test")
    parser.add_argument("function", help="Patch factory function name")
    parser.add_argument("--width", type=int, default=800)
    parser.add_argument("--height", type=int, default=600)
    parser.add_argument("--fps", type=int, default=60, help="Target frame rate")
    parser.add_argument("--hot-reload-shaders", action="store_true", default=False)
    parser.add_argument("--log-level", type=str, default="INFO",
                        choices=["FATAL", "ERROR", "WARNING", "INFO", "DEBUG", "TRACE"],
                        help="Logging level")
    parser.add_argument("--log-file", type=str, default=None, help="Optional log file path")

    args = parser.parse_args()

    configure_logging(level=args.log_level, log_to_file=args.log_file is not None, log_file_path=args.log_file)

    try:
        patch = _load_patch(args.module, args.function, args.width, args.height)
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

    engine_thread = threading.Thread(target=engine.run, daemon=True)
    engine_thread.start()

    def reload_patch() -> None:
        module = importlib.import_module(args.module)
        importlib.reload(module)
        engine.patch = _load_patch(args.module, args.function, args.width, args.height)
        info("Patch reloaded")

    banner = (
        "Oblique REPL.\n"
        "Edit your patch and call reload_patch() to apply changes.\n"
        "The running engine is available as 'engine'."
    )
    console_locals = {"engine": engine, "reload_patch": reload_patch}
    code.InteractiveConsole(console_locals).interact(banner=banner)


if __name__ == "__main__":
    main()

