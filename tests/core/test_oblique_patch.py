from pathlib import Path
from tests.utils.stubs import setup_stubs, load_module

ROOT = Path(__file__).resolve().parents[2]


def test_tick_returns_callback_result():
    setup_stubs()
    patch_mod = load_module("core.oblique_patch", ROOT / "core" / "oblique_patch.py")

    def callback(t: float):
        return f"module_{t}"

    patch = patch_mod.ObliquePatch(callback)
    assert patch.tick(1.0) == "module_1.0"
    assert patch.audio_output is None
