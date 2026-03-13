"""Tests for the ControlBridge IPC layer."""

import multiprocessing

from core.control_ipc import ControlBridge
from core.param_store import ParamStore


def _make_bridge_and_conn():
    """Create a ControlBridge with a real Pipe for testing."""
    parent_conn, child_conn = multiprocessing.Pipe()
    store = ParamStore()
    store.register(name="speed", group="Cube", default=1.0, min=0.0, max=5.0)
    bridge = ControlBridge(parent_conn, store)
    return bridge, child_conn, store


def test_send_telemetry():
    bridge, child, _ = _make_bridge_and_conn()
    bridge._last_telemetry = 0  # force send
    bridge.send_telemetry({"fps": 60.0})
    assert child.poll(0.1)
    msg = child.recv()
    assert msg[0] == "telemetry"
    assert msg[1]["fps"] == 60.0
    bridge.close()
    child.close()


def test_send_telemetry_throttled():
    bridge, child, _ = _make_bridge_and_conn()
    bridge.send_telemetry({"fps": 60.0})
    # Second call within 100ms should be suppressed
    bridge.send_telemetry({"fps": 61.0})
    child.recv()  # first message
    assert not child.poll(0.01)  # no second message
    bridge.close()
    child.close()


def test_send_params_snapshot():
    bridge, child, _ = _make_bridge_and_conn()
    bridge.send_params_snapshot()
    msg = child.recv()
    assert msg[0] == "params_snapshot"
    assert "Cube.speed" in msg[1]
    assert msg[1]["Cube.speed"]["value"] == 1.0
    bridge.close()
    child.close()


def test_send_param_update():
    bridge, child, _ = _make_bridge_and_conn()
    bridge.send_param_update("Cube.speed", 3.0)
    msg = child.recv()
    assert msg == ("param_update", "Cube.speed", 3.0)
    bridge.close()
    child.close()


def test_send_log():
    bridge, child, _ = _make_bridge_and_conn()
    bridge.send_log("ERROR", "boom")
    msg = child.recv()
    assert msg == ("log", "ERROR", "boom")
    bridge.close()
    child.close()


def test_send_status():
    bridge, child, _ = _make_bridge_and_conn()
    bridge.send_status({"patch": "demo"})
    msg = child.recv()
    assert msg[0] == "status"
    assert msg[1]["patch"] == "demo"
    bridge.close()
    child.close()


def test_mark_dirty_sends_snapshot():
    bridge, child, _ = _make_bridge_and_conn()
    bridge.mark_dirty()
    msg = child.recv()
    assert msg[0] == "params_snapshot"
    bridge.close()
    child.close()


def test_poll_incoming_set_param():
    bridge, child, store = _make_bridge_and_conn()
    child.send(("set_param", "Cube.speed", 4.0))
    result = bridge.poll_incoming()
    assert result is None
    assert store.get("Cube.speed") == 4.0
    bridge.close()
    child.close()


def test_poll_incoming_quit():
    bridge, child, _ = _make_bridge_and_conn()
    child.send(("quit",))
    result = bridge.poll_incoming()
    assert result == "quit"
    bridge.close()
    child.close()


def test_poll_incoming_reload():
    bridge, child, _ = _make_bridge_and_conn()
    child.send(("reload",))
    result = bridge.poll_incoming()
    assert result == "reload"
    bridge.close()
    child.close()


def test_poll_incoming_empty():
    bridge, child, _ = _make_bridge_and_conn()
    result = bridge.poll_incoming()
    assert result is None
    bridge.close()
    child.close()


def test_close_idempotent():
    bridge, child, _ = _make_bridge_and_conn()
    bridge.close()
    bridge.close()  # should not raise
    child.close()
