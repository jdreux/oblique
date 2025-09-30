"""Command line interface for the Oblique AV engine.

The CLI consolidates the old shell scripts into a structured ``argparse`` based
interface.  It provides a ``start`` command for launching patches or a REPL
workspace.  Every sub-command supports ``--dry-run`` for surfacing the resolved
configuration without launching the engine and exposes shared flags for
logging, window configuration and shader reloading.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import os
import re
import sys
import textwrap
import time
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from types import ModuleType
from typing import Callable, Optional, Sequence, Tuple

from core.logger import configure_logging, error, info
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
    hot_reload_shaders: bool
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

    if args.target is None or args.target == "repl":
        raise CliError(
            cause="No patch was provided to 'oblique start'.",
            hint="Pass a module path like 'projects.demo.demo_audio_file' or a patch file path.",
            exit_code=ExitCode.USAGE,
        )

    if args.extra_target is not None:
        raise CliError(
            cause="Unexpected extra positional argument provided to 'oblique start'.",
            hint="Use 'oblique start repl [--patch …]' or 'oblique start <patch>'.",
            exit_code=ExitCode.USAGE,
        )

    if args.hot_reload_python:
        raise CliError(
            cause="Python hot reload is only available when launching the REPL.",
            hint="Run 'oblique start repl --hot-reload-python'.",
            exit_code=ExitCode.USAGE,
        )

    patch_ref = parse_patch_reference(args.target)
    return StartConfiguration(
        patch=patch_ref,
        width=args.width,
        height=args.height,
        fps=args.fps,
        monitor=args.monitor,
        hot_reload_shaders=args.hot_reload_shaders,
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
        Shader hot reload: {'enabled' if config.hot_reload_shaders else 'disabled'}
        """
    ).strip()

    return plan


def run_start(args: argparse.Namespace) -> ExitCode:
    """Implementation of the ``oblique start`` command."""

    if args.target == "repl":
        repl_args = argparse.Namespace(
            patch=args.extra_target,
            width=args.width,
            height=args.height,
            fps=args.fps,
            log_level=args.log_level,
            log_file=args.log_file,
            dry_run=args.dry_run,
            hot_reload_shaders=args.hot_reload_shaders,
            hot_reload_python=args.hot_reload_python,
        )
        return run_repl(repl_args)

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
        patch, _, _ = instantiate_patch(
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
        hot_reload_shaders=config.hot_reload_shaders,
        monitor=config.monitor,
    )

    try:
        engine.run()
    except KeyboardInterrupt:
        info("Shutting down…")
        return ExitCode.OK
    except Exception as exc:  # pragma: no cover - depends on runtime env
        error(f"Engine error: {exc}")
        return ExitCode.INTERNAL

    return ExitCode.OK


def ensure_repl_template() -> Tuple[str, Path, bool]:
    """Ensure the REPL sandbox template exists and return its metadata."""

    override = os.environ.get("OBLIQUE_REPL_DIR")
    sandbox_dir = Path(override).expanduser() if override else Path.cwd() / REPL_SANDBOX_DIR_NAME
    sandbox_dir.mkdir(parents=True, exist_ok=True)
    target = sandbox_dir / "repl_patch.py"

    created = False
    if target.exists():
        if target.is_dir():
            raise CliError(
                cause=f"REPL template path '{target}' is a directory.",
                hint="Remove the directory or set OBLIQUE_REPL_DIR to a writable location.",
                exit_code=ExitCode.IO,
            )
    else:
        try:
            target.write_text(_read_repl_template(), encoding="utf-8")
        except OSError as exc:
            raise CliError(
                cause=f"Unable to write REPL template to '{target}'.",
                hint="Check filesystem permissions or available disk space.",
                exit_code=ExitCode.IO,
            ) from exc
        created = True

    module_name = "repl_patch"

    sandbox_path = str(sandbox_dir.resolve())
    if sandbox_path not in sys.path:
        sys.path.insert(0, sandbox_path)

    return module_name, target, created


def run_repl(args: argparse.Namespace) -> ExitCode:
    """Implementation of the REPL workflow dispatched through ``oblique start``."""

    patch_module: str
    patch_function: str
    created_file: Optional[Path] = None
    created = False

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
            patch_module, created_file, created = ensure_repl_template()
            patch_function = "temp_patch"
        except CliError as err:
            print_cli_error(err)
            return err.exit_code

    plan_lines = [
        f"Patch module: {patch_module}:{patch_function}",
        f"Resolution: {args.width}x{args.height}",
        f"FPS: {args.fps}",
    ]
    plan_lines.append(
        "Shader hot reload: "
        + ("enabled" if args.hot_reload_shaders else "disabled")
    )
    plan_lines.append(
        "Python hot reload: "
        + ("enabled" if args.hot_reload_python else "disabled")
    )
    plan_lines.append(
        "Logging: level="
        + args.log_level
        + (f" file={args.log_file}" if args.log_file else "")
    )

    if created_file is not None:
        state = "created" if args.patch is None and created else "existing"
        plan_lines.append(f"Template path ({state}): {created_file}")

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
    if args.hot_reload_shaders:
        repl_args.append("--hot-reload-shaders")
    if args.hot_reload_python:
        repl_args.append("--hot-reload-python")

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
    subparsers.required = True

    start_parser = subparsers.add_parser("start", help="Launch a patch or REPL")
    start_parser.add_argument(
        "target",
        nargs="?",
        help="Patch module path, patch file, or 'repl' to open the interactive workspace",
    )
    start_parser.add_argument(
        "extra_target",
        nargs="?",
        help="Optional patch reference when launching the REPL",
    )
    start_parser.add_argument("--width", type=int, default=800)
    start_parser.add_argument("--height", type=int, default=600)
    start_parser.add_argument("--fps", type=int, default=60)
    start_parser.add_argument("--monitor", type=int, default=None)
    start_parser.add_argument(
        "--hot-reload-shaders",
        action="store_true",
        help="Reload GLSL shaders when files change",
    )
    start_parser.add_argument(
        "--hot-reload-python",
        action="store_true",
        help="Reload the patch module automatically (REPL only)",
    )
    start_parser.add_argument("--log-level", default="INFO")
    start_parser.add_argument("--log-file")
    start_parser.add_argument("--dry-run", action="store_true")
    start_parser.set_defaults(func=run_start)

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

