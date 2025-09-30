"""Tests for the top-level CLI helpers."""

from argparse import Namespace
from types import ModuleType
import importlib
import sys

import pytest

# ``cli`` imports ``sounddevice`` via ``core.oblique_engine``; provide a stub so
# the tests don't require native PortAudio bindings.
sys.modules.setdefault("sounddevice", ModuleType("sounddevice"))

logger_module = sys.modules.get("core.logger")
if logger_module is None:
    logger_module = importlib.import_module("core.logger")
elif not hasattr(logger_module, "configure_logging"):
    logger_module.configure_logging = lambda *args, **kwargs: None  # type: ignore[attr-defined]
    logger_module.error = getattr(logger_module, "error", lambda *a, **k: None)
    logger_module.info = getattr(logger_module, "info", lambda *a, **k: None)
    logger_module.warning = getattr(logger_module, "warning", lambda *a, **k: None)

from cli import CliError, ExitCode, resolve_start_configuration


def test_start_requires_patch_argument() -> None:
    """``oblique start`` must refuse to run without an explicit patch target."""

    args = Namespace(
        patch=None,
        width=800,
        height=600,
        fps=60,
        monitor=None,
        watch=False,
        log_level="INFO",
        log_file=None,
    )

    with pytest.raises(CliError) as err:
        resolve_start_configuration(args)

    assert err.value.exit_code == ExitCode.USAGE
