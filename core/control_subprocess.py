"""Spawn the Textual TUI in a subprocess and return an IPC bridge.

Uses ``subprocess.Popen`` with a dedicated entry point to avoid
re-importing ``__main__`` (the ``spawn`` problem on Python 3.13) and
to avoid ``fork`` with loaded ObjC libs on macOS.

IPC uses a Unix domain socket wrapped in
``multiprocessing.connection.Connection`` for pickle-framed messaging.
The child connects to a named socket (no ``pass_fds``, so ``Popen``
can use ``posix_spawn`` instead of ``fork+exec``).

Crash log: ~/.oblique_tui_crash.log
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
from multiprocessing.connection import Connection

from core.control_ipc import ControlBridge
from core.param_store import ParamStore

CRASH_LOG = os.path.expanduser("~/.oblique_tui_crash.log")

_TERMINAL_RESET = (
    "\033[?1049l"   # exit alternate screen buffer
    "\033[?1000l"   # disable mouse click tracking
    "\033[?1002l"   # disable mouse drag tracking
    "\033[?1003l"   # disable mouse any-event tracking
    "\033[?1006l"   # disable SGR mouse mode
    "\033[?1015l"   # disable urxvt mouse mode
    "\033[?25h"     # show cursor
    "\033[0m"       # reset all attributes
)


def _resolve_tty_path() -> str:
    """Resolve the real tty device path (e.g. /dev/ttys003).

    The subprocess has no controlling terminal (stdin/stdout/stderr are
    DEVNULL/PIPE), so ``/dev/tty`` won't work there.  We must resolve the
    actual device path (e.g. ``/dev/ttys003``) in the parent and pass it.
    """
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            if hasattr(stream, "fileno"):
                return os.ttyname(stream.fileno())
        except (OSError, ValueError, AttributeError):
            continue

    # Last resort: open /dev/tty (works in parent), get its real path
    try:
        fd = os.open("/dev/tty", os.O_RDONLY)
        try:
            return os.ttyname(fd)
        finally:
            os.close(fd)
    except OSError:
        pass

    return "/dev/tty"


def spawn_control_tui(store: ParamStore) -> tuple[ControlBridge, subprocess.Popen]:
    """Spawn the TUI subprocess and return (bridge, process).

    Uses ``subprocess.Popen`` with a dedicated entry point module
    (``core.control_tui_main``), avoiding both the ``spawn`` re-import
    problem and the ``fork`` ObjC crash on macOS.

    IPC uses a Unix domain socket.  The parent binds and listens; the
    child connects by path.  No ``pass_fds`` means ``Popen`` can use
    ``posix_spawn`` on macOS — no ``fork``, no ObjC issues.
    """
    tty_path = _resolve_tty_path()

    # Create a Unix domain socket for IPC
    sock_path = tempfile.mktemp(prefix="oblique_ipc_", suffix=".sock")
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(sock_path)
    server.listen(1)

    process = subprocess.Popen(
        [sys.executable, "-m", "core.control_tui_main", tty_path, sock_path],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait for child to connect (with timeout so we don't hang if it dies)
    server.settimeout(10.0)
    try:
        conn_sock, _ = server.accept()
    except socket.timeout:
        server.close()
        os.unlink(sock_path)
        process.kill()
        raise RuntimeError("TUI subprocess failed to connect (see ~/.oblique_tui_crash.log)")
    finally:
        server.close()
        try:
            os.unlink(sock_path)
        except FileNotFoundError:
            pass

    # Wrap in Connection for pickle framing
    parent_conn = Connection(conn_sock.detach())
    bridge = ControlBridge(parent_conn, store)
    return bridge, process
