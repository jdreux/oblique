"""Command line interface for the Oblique AV engine.

The CLI consolidates the old shell scripts into a structured ``argparse`` based
interface.  It provides a ``start`` command for launching patches and a ``repl``
workflow for rapid iteration.  Every sub-command supports ``--dry-run`` for
surfacing the resolved configuration without launching the engine and exposes
shared flags for logging, window configuration and shader reloading.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import os
import re
import sys
import textwrap
import threading
import time
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from types import ModuleType
from typing import Callable, Optional, Sequence, Tuple

from core.logger import configure_logging, error, info, warning
from core.oblique_engine import ObliqueEngine
from core.oblique_patch import ObliquePatch
from core.paths import resolve_asset_path
REPL_SANDBOX_DIR_NAME = ".oblique"


class ExitCode(IntEnum):
    """Enumerate CLI exit codes for consistent error handling."""

    OK = 0
    USAGE = 2
    MISSING_DEPENDENCY = 10
    DEVICE = 20
    GPU = 30
    IO = 40
    INTERNAL = 50


class CliError(RuntimeError):
    """Structured error with actionable hint and exit code."""

    def __init__(self, cause: str, hint: str, exit_code: ExitCode) -> None:
        super().__init__(cause)
        self.cause = cause
        self.hint = hint
        self.exit_code = exit_code


@dataclass
class PatchReference:
    """Patch descriptor storing module or file source information."""

    module_name: str
    function_name: str
    kind: str  # either "module" or "file"
    source: str

    def load_module(self, reload: bool = False) -> ModuleType:
        """Return a module object for this patch reference."""

        if self.kind == "module":
            try:
                if reload and self.module_name in sys.modules:
                    module = importlib.reload(sys.modules[self.module_name])
                else:
                    module = importlib.import_module(self.module_name)
            except ModuleNotFoundError as exc:
                raise CliError(
                    cause=f"Patch module '{self.module_name}' could not be imported.",
                    hint="Ensure the module is on PYTHONPATH or provide a file path.",
                    exit_code=ExitCode.USAGE,
                ) from exc
            return module

        path = Path(self.source)
        if reload and self.module_name in sys.modules:
            del sys.modules[self.module_name]

        spec = importlib.util.spec_from_file_location(self.module_name, path)
        if spec is None or spec.loader is None:
            raise CliError(
                cause=f"Failed to load patch from '{path}'.",
                hint="Ensure the file exists and is a valid Python module.",
                exit_code=ExitCode.IO,
            )

        module = importlib.util.module_from_spec(spec)
        sys.modules[self.module_name] = module
        try:
            spec.loader.exec_module(module)
        except FileNotFoundError as exc:
            raise CliError(
                cause=f"Patch file '{path}' not found.",
                hint="Verify the path or run with an existing module.",
                exit_code=ExitCode.IO,
            ) from exc
        return module

@dataclass
class StartConfiguration:
    """Resolved configuration for ``oblique start``."""

    patch: PatchReference
    width: int
    height: int
    fps: int
    monitor: Optional[int]
    watch: bool
    log_level: str
    log_file: Optional[str]


def print_cli_error(err: CliError) -> None:
    """Pretty-print a CLI error with hint information."""

    sys.stderr.write(f"error: {err.cause}\n")
    if err.hint:
        sys.stderr.write(f"hint: {err.hint}\n")


def sanitize_module_name(path: Path) -> str:
    """Create a deterministic module name for a patch file path."""

    sanitized = re.sub(r"\W+", "_", str(path.with_suffix("")))
    return f"oblique_patch_{abs(hash(sanitized))}"


def parse_patch_reference(raw: str) -> PatchReference:
    """Parse user supplied patch target into a :class:`PatchReference`."""

    target = raw
    if ":" in target:
        module_part, function = target.split(":", 1)
    else:
        module_part, function = target, "oblique_patch"

    candidate = Path(module_part)
    if candidate.exists() and candidate.suffix == ".py":
        module_name = sanitize_module_name(candidate.resolve())
        return PatchReference(
            module_name=module_name,
            function_name=function,
            kind="file",
            source=str(candidate.resolve()),
        )

    module_name = module_part.replace("/", ".")
    return PatchReference(
        module_name=module_name,
        function_name=function,
        kind="module",
        source=module_name,
    )


def instantiate_patch(
    patch_ref: PatchReference,
    width: int,
    height: int,
    reload: bool = False,
) -> Tuple[ObliquePatch, ModuleType, Path]:
    """Instantiate a patch from a reference and return module + file path."""

    module = patch_ref.load_module(reload=reload)
    if not hasattr(module, patch_ref.function_name):
        raise CliError(
            cause=(
                f"Patch function '{patch_ref.function_name}' not found in module "
                f"'{patch_ref.module_name}'."
            ),
            hint="Use module:function syntax or update the patch file.",
            exit_code=ExitCode.USAGE,
        )

    factory: Callable[[int, int], ObliquePatch] = getattr(
        module, patch_ref.function_name
    )

    patch = factory(width * 2, height * 2)
    module_path = Path(module.__file__).resolve() if module.__file__ else Path()
    return patch, module, module_path

def resolve_start_configuration(args: argparse.Namespace) -> StartConfiguration:
    """Translate parsed arguments into a :class:`StartConfiguration`."""

    if args.patch is None:
        raise CliError(
            cause="No patch was provided to 'oblique start'.",
            hint="Pass a module path like 'projects.demo.demo_audio_file' or a patch file path.",
            exit_code=ExitCode.USAGE,
        )

    patch_ref = parse_patch_reference(args.patch)
    return StartConfiguration(
        patch=patch_ref,
        width=args.width,
        height=args.height,
        fps=args.fps,
        monitor=args.monitor,
        watch=args.watch,
        log_level=args.log_level,
        log_file=args.log_file,
    )


def format_start_plan(config: StartConfiguration) -> str:
    """Return a human readable description of the start configuration."""

    plan = textwrap.dedent(
        f"""
        Patch: {config.patch.module_name}:{config.patch.function_name}
        Window: {config.width}x{config.height} @ {config.fps} fps
        Monitor: {config.monitor if config.monitor is not None else 'default'}
        Logging: level={config.log_level}{' file=' + config.log_file if config.log_file else ''}
        Watch mode: {'enabled (patch + shaders)' if config.watch else 'disabled'}
        """
    ).strip()

    return plan


class PatchWatcher(threading.Thread):
    """Monitor patch files and hot reload modules when they change."""

    def __init__(
        self,
        engine: ObliqueEngine,
        config: StartConfiguration,
        module_path: Path,
    ) -> None:
        super().__init__(daemon=True)
        self.engine = engine
        self.config = config
        self.module_path = module_path
        self._stop_event = threading.Event()
        self._last_mtime = self._get_mtime()

    def _get_mtime(self) -> float:
        try:
            return self.module_path.stat().st_mtime
        except FileNotFoundError:
            return 0.0

    def stop(self) -> None:
        """Stop watching for file changes."""

        self._stop_event.set()

    def run(self) -> None:  # pragma: no cover - requires filesystem + render loop
        if not self.module_path:
            return

        info(f"Watching {self.module_path} for patch changes")
        while not self._stop_event.wait(0.5):
            current_mtime = self._get_mtime()
            if current_mtime <= self._last_mtime:
                continue

            self._last_mtime = current_mtime
            try:
                new_patch, _, _ = instantiate_patch(
                    self.config.patch,
                    self.config.width,
                    self.config.height,
                    reload=True,
                )
                self.engine.patch = new_patch
                info("Patch reloaded successfully")
            except CliError as cli_err:
                warning(f"Patch reload failed: {cli_err.cause}")
            except Exception as exc:  # pragma: no cover - defensive logging
                error(f"Patch reload failed: {exc}")

def run_start(args: argparse.Namespace) -> ExitCode:
    """Implementation of the ``oblique start`` command."""

    try:
        config = resolve_start_configuration(args)
    except CliError as err:
        print_cli_error(err)
        return err.exit_code

    plan = format_start_plan(config)

    if args.dry_run:
        print(plan)
        return ExitCode.OK

    configure_logging(
        level=config.log_level,
        log_to_file=config.log_file is not None,
        log_file_path=config.log_file,
    )

    info(plan)

    try:
        patch, module, module_path = instantiate_patch(
            config.patch,
            config.width,
            config.height,
        )
    except CliError as err:
        print_cli_error(err)
        return err.exit_code
    except Exception as exc:  # pragma: no cover - defensive logging
        error(f"Unexpected error while loading patch: {exc}")
        return ExitCode.INTERNAL

    engine = ObliqueEngine(
        patch=patch,
        width=config.width,
        height=config.height,
        target_fps=config.fps,
        hot_reload_shaders=config.watch,
        monitor=config.monitor,
    )

    watcher: Optional[PatchWatcher] = None
    if config.watch and module_path:
        watcher = PatchWatcher(engine, config, module_path)
        watcher.start()

    try:
        engine.run()
    except KeyboardInterrupt:
        info("Shutting down…")
        return ExitCode.OK
    except Exception as exc:  # pragma: no cover - depends on runtime env
        error(f"Engine error: {exc}")
        return ExitCode.INTERNAL
    finally:
        if watcher is not None:
            watcher.stop()

    return ExitCode.OK


def ensure_repl_template() -> Tuple[str, Path]:
    """Create (if necessary) and return the REPL sandbox module name and file."""

    override = os.environ.get("OBLIQUE_REPL_DIR")
    sandbox_dir = Path(override).expanduser() if override else Path.cwd() / REPL_SANDBOX_DIR_NAME
    sandbox_dir.mkdir(parents=True, exist_ok=True)
    target = sandbox_dir / "repl_patch.py"

    target.write_text(_read_repl_template())
    module_name = "repl_patch"

    if str(sandbox_dir.resolve()) not in sys.path:
        sys.path.insert(0, str(sandbox_dir.resolve()))

    return module_name, target


def run_repl(args: argparse.Namespace) -> ExitCode:
    """Implementation of the ``oblique repl start`` command."""

    patch_module: str
    patch_function: str
    created_file: Optional[Path] = None

    if args.patch is not None:
        try:
            patch_ref = parse_patch_reference(args.patch)
            patch_ref.load_module()
        except CliError as err:
            print_cli_error(err)
            return err.exit_code

        patch_module = patch_ref.module_name
        patch_function = patch_ref.function_name
    else:
        try:
            patch_module, created_file = ensure_repl_template()
            patch_function = "temp_patch"
        except CliError as err:
            print_cli_error(err)
            return err.exit_code

    plan_lines = [
        f"Patch module: {patch_module}:{patch_function}",
        f"Resolution: {args.width}x{args.height}",
        f"FPS: {args.fps}",
        f"Watch mode: {'enabled' if args.watch else 'disabled'}",
    ]
    plan_lines.append(
        "Shader hot reload: "
        + ("enabled" if args.watch else "disabled")
    )
    plan_lines.append(
        "Logging: level="
        + args.log_level
        + (f" file={args.log_file}" if args.log_file else "")
    )

    if created_file is not None:
        plan_lines.append(f"Template path: {created_file}")

    plan = "\n".join(plan_lines)
    info(plan)

    if args.dry_run:
        print(plan)
        return ExitCode.OK

    repl_args = [
        "repl",
        patch_module,
        patch_function,
        "--width",
        str(args.width),
        "--height",
        str(args.height),
        "--fps",
        str(args.fps),
        "--log-level",
        args.log_level,
    ]

    if args.log_file:
        repl_args.extend(["--log-file", args.log_file])
    if args.watch:
        repl_args.append("--hot-reload-shaders")

    original_argv = sys.argv
    try:
        sys.argv = repl_args
        import repl as repl_module

        repl_module.main()
    finally:
        sys.argv = original_argv

    return ExitCode.OK


def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level argument parser."""

    parser = argparse.ArgumentParser(prog="oblique", description="Oblique CLI")

    subparsers = parser.add_subparsers(dest="command")

    start_parser = subparsers.add_parser("start", help="Launch a patch")
    start_parser.add_argument("patch", nargs="?", help="Patch module path or file")
    start_parser.add_argument("--width", type=int, default=800)
    start_parser.add_argument("--height", type=int, default=600)
    start_parser.add_argument("--fps", type=int, default=60)
    start_parser.add_argument("--monitor", type=int, default=None)
    start_parser.add_argument("--watch", action="store_true", help="Watch patch file for reload")
    start_parser.add_argument("--log-level", default="INFO")
    start_parser.add_argument("--log-file")
    start_parser.add_argument("--dry-run", action="store_true")
    start_parser.set_defaults(func=run_start)

    repl_parser = subparsers.add_parser("repl", help="Interactive REPL tools")
    repl_subparsers = repl_parser.add_subparsers(dest="repl_command", required=True)

    repl_start = repl_subparsers.add_parser("start", help="Start REPL with optional template")
    repl_start.add_argument("patch", nargs="?", help="Existing patch module or file")
    repl_start.add_argument("--width", type=int, default=800)
    repl_start.add_argument("--height", type=int, default=600)
    repl_start.add_argument("--fps", type=int, default=60)
    repl_start.add_argument("--watch", action="store_true")
    repl_start.add_argument("--log-level", default="INFO")
    repl_start.add_argument("--log-file")
    repl_start.add_argument("--dry-run", action="store_true")
    repl_start.set_defaults(func=run_repl)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entry point."""

    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return ExitCode.USAGE

    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(main())

def _read_repl_template() -> str:
    """Return the default REPL template source bundled with the package."""

    template_path = resolve_asset_path("core/default_repl_template.py")
    if not template_path.exists():
        raise CliError(
            cause="REPL template file is missing from the installation.",
            hint="Reinstall Oblique so package data such as core/default_repl_template.py is available.",
            exit_code=ExitCode.IO,
        )
    return template_path.read_text(encoding="utf-8")

