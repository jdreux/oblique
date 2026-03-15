"""Standalone subprocess entry point for the Textual TUI.

Invoked as: python -m core.control_tui_main <tty_path> <socket_path>

Never imports cli.py, oblique_engine, glfw, moderngl, or sounddevice.
"""

import atexit
import faulthandler
import io
import os
import socket
import sys
import traceback

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

# -- Early crash capture ------------------------------------------------------
_crash_fd = os.open(CRASH_LOG, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_APPEND, 0o644)
faulthandler.enable(file=_crash_fd)

_tty_out = None


def _write_crash(msg: str) -> None:
    """Append a message to the crash log fd."""
    try:
        os.write(_crash_fd, msg.encode())
    except OSError:
        pass


def _excepthook(exc_type, exc_value, exc_tb):
    """Write unhandled exceptions to the crash log."""
    try:
        lines = traceback.format_exception(exc_type, exc_value, exc_tb)
        _write_crash("".join(lines))
    except Exception:
        _write_crash(f"excepthook failed: {exc_type}: {exc_value}\n")


sys.excepthook = _excepthook


def _atexit_reset():
    """Best-effort terminal reset on exit."""
    if _tty_out is not None:
        try:
            _tty_out.write(_TERMINAL_RESET)
            _tty_out.flush()
        except Exception:
            pass
    try:
        os.system("stty sane 2>/dev/null")
    except Exception:
        pass


atexit.register(_atexit_reset)


def main() -> None:
    global _tty_out

    if len(sys.argv) < 3:
        _write_crash("usage: python -m core.control_tui_main <tty_path> <socket_path>\n")
        sys.exit(2)

    tty_path = sys.argv[1]
    sock_path = sys.argv[2]

    # Reopen tty for Textual — must replace actual fds 0/1/2, not just
    # sys.stdin wrappers, because Textual checks os.isatty(0) etc.
    try:
        fd_in = os.open(tty_path, os.O_RDONLY)
        fd_out = os.open(tty_path, os.O_WRONLY)
    except OSError as e:
        _write_crash(f"Failed to open tty {tty_path!r}: {e}\n")
        sys.exit(1)

    # Replace raw fds 0/1/2 so Textual sees real tty descriptors
    os.dup2(fd_in, 0)
    os.dup2(fd_out, 1)
    os.dup2(fd_out, 2)
    os.close(fd_in)
    os.close(fd_out)

    tty_in = io.TextIOWrapper(io.FileIO(0, "r", closefd=False))
    _tty_out = io.TextIOWrapper(io.FileIO(1, "w", closefd=False))
    tty_err = io.TextIOWrapper(io.FileIO(2, "w", closefd=False))

    sys.stdin = tty_in
    sys.__stdin__ = tty_in  # type: ignore[assignment]
    sys.stdout = _tty_out
    sys.__stdout__ = _tty_out  # type: ignore[assignment]
    sys.stderr = tty_err
    sys.__stderr__ = _tty_out  # type: ignore[assignment]

    # Connect to parent's Unix domain socket, wrap in Connection (pickle framing)
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.connect(sock_path)
    except OSError as e:
        _write_crash(f"Failed to connect to IPC socket {sock_path!r}: {e}\n")
        sys.exit(1)

    from multiprocessing.connection import Connection

    conn = Connection(sock.detach())

    # Only now import Textual (heavy dep, but no GPU/audio libs)
    from core.control_tui import ControlTUI

    app = ControlTUI(conn)
    app.run()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BaseException:
        _write_crash(traceback.format_exc())
        sys.exit(1)
