"""Spawn the Textual TUI in a subprocess and return an IPC bridge."""

from __future__ import annotations

import multiprocessing
from multiprocessing.connection import Connection

from core.control_ipc import ControlBridge
from core.param_store import ParamStore


def _run_tui_process(conn: Connection) -> None:
    """Subprocess entry point — runs the Textual TUI app.

    Reopens /dev/tty as stdin/stdout/stderr so Textual can drive the
    terminal even when the parent process has consumed the original fds.
    """
    import io
    import os
    import sys

    # Open /dev/tty for read and write separately
    fd_in = os.open("/dev/tty", os.O_RDONLY)
    fd_out = os.open("/dev/tty", os.O_WRONLY)

    tty_in = io.TextIOWrapper(io.FileIO(fd_in, "r", closefd=True))
    tty_out = io.TextIOWrapper(io.FileIO(fd_out, "w", closefd=True))

    sys.stdin = tty_in
    sys.__stdin__ = tty_in  # type: ignore[assignment]
    sys.stdout = tty_out
    sys.__stdout__ = tty_out  # type: ignore[assignment]
    sys.stderr = tty_out
    sys.__stderr__ = tty_out  # type: ignore[assignment]

    from core.control_tui import ControlTUI

    app = ControlTUI(conn)
    app.run()


def spawn_control_tui(store: ParamStore) -> tuple[ControlBridge, multiprocessing.Process]:
    """Spawn the TUI subprocess and return (bridge, process)."""
    parent_conn, child_conn = multiprocessing.Pipe()
    process = multiprocessing.Process(
        target=_run_tui_process,
        args=(child_conn,),
        daemon=True,
    )
    process.start()
    child_conn.close()  # Parent doesn't need the child end
    bridge = ControlBridge(parent_conn, store)
    return bridge, process
