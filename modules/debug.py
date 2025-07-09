from .base_av_module import BaseAVModule, BaseAVParams
from typing import Any, Dict
from dataclasses import dataclass
import numpy as np
from core.oblique_node import ObliqueNode
from processing.base_processing_operator import BaseProcessingOperator


@dataclass
class DebugParams(BaseAVParams):
    number: float = 0.0
    text: str = "Debug"
    width: int = 800
    height: int = 600


class DebugModule(BaseAVModule[DebugParams]):
    """
    Debug module that displays an input number and string using a shader.
    """

    metadata = {
        "name": "DebugModule",
        "description": "Displays an input number and string for debugging purposes.",
        "parameters": {"number": float, "text": str},
    }
    frag_shader_path = "shaders/debug.frag"

    def __init__(
        self,
        params: DebugParams = DebugParams(),
        number_input: BaseProcessingOperator | None = None,
    ):
        super().__init__(params, number_input)
        self.number_input = number_input

    def render_data(self, t: float) -> dict[str, Any]:
        # Return shader path and uniforms for rendering
        if self.number_input:
            number = self.number_input.process()
            print(f"Number: {number}")
        else:
            number = self.params.number
        return {
            "frag_shader_path": self.frag_shader_path,
            "uniforms": {
                "u_number": number,
                "u_resolution": (self.params.width, self.params.height),
                # Text uniform would require a text rendering system; placeholder for now
                # "u_text": self.params.text
            },
        }


if __name__ == "__main__":
    mod = DebugModule(DebugParams(number=42.0, text="Hello, Oblique!"))
    print("Initial render:", mod.render_data(0.0))
    print("After update:", mod.render_data(1.0))
