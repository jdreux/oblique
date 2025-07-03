from .base_av_module import BaseAVModule, BaseAVParams
from typing import Any, Dict
from dataclasses import dataclass
import numpy as np

@dataclass
class DebugParams(BaseAVParams):
    number: float = 0.0
    text: str = "Debug"
    width: int = 800
    height: int = 600

class DebugModule(BaseAVModule):
    """
    Debug module that displays an input number and string using a shader.
    """
    metadata = {
        "name": "DebugModule",
        "description": "Displays an input number and string for debugging purposes.",
        "parameters": {
            "number": float,
            "text": str
        }
    }
    frag_shader_path = "shaders/debug.frag"

    def __init__(self, params: DebugParams = DebugParams()):
        super().__init__(params)

    def update(self, params: DebugParams) -> None:
        if not isinstance(params, DebugParams):
            params = DebugParams(**params.__dict__)
        self.params = params

    def render(self, t: float) -> dict[str, Any]:
        # Return shader path and uniforms for rendering
        return {
            "frag_shader_path": self.frag_shader_path,
            "uniforms": {
                "u_number": self.params.number,
                "u_resolution": (self.params.width, self.params.height),
                # Text uniform would require a text rendering system; placeholder for now
                # "u_text": self.params.text
            }
        }

if __name__ == "__main__":
    mod = DebugModule(DebugParams(number=42.0, text="Hello, Oblique!"))
    print("Initial render:", mod.render(0.0))
    mod.update(DebugParams(number=3.14, text="Updated!"))
    print("After update:", mod.render(1.0)) 