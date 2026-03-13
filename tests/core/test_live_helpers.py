from dataclasses import dataclass, field
from unittest.mock import MagicMock

from core.live_helpers import register_module_params
from core.param_store import ParamStore
from modules.core.base_av_module import BaseAVParams


@dataclass
class FakeParams(BaseAVParams):
    speed: float = field(
        default=1.0,
        metadata={"min": 0.0, "max": 5.0, "description": "Speed."},
    )
    brightness: float = field(
        default=0.5,
        metadata={"min": 0.0, "max": 1.0, "description": "Bright."},
    )


def test_register_module_params():
    store = ParamStore()
    module = MagicMock()
    module.__class__.__name__ = "TestModule"
    module.params = FakeParams(width=800, height=600)

    register_module_params(module, store, group="Test")

    assert "Test.speed" in store
    assert "Test.brightness" in store
    assert store.get("Test.speed") == 1.0

    # Check that the param was wired to a callable
    assert callable(module.params.speed)
    store.set("Test.speed", 3.0)
    assert module.params.speed() == 3.0
