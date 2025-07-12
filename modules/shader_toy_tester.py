from .base_av_module import BaseAVModule, BaseAVParams, Uniforms
from typing import Any, Dict, Tuple
from dataclasses import dataclass


@dataclass
class ShaderToyTesterParams(BaseAVParams):
    width: int = 800
    height: int = 600


class ShaderToyTesterUniforms(Uniforms, total=True):
    iTime: float
    iResolution: Tuple[int, int]
    iMouse: Tuple[float, float, float, float]
    iFrame: int


class ShaderToyTesterModule(BaseAVModule[ShaderToyTesterParams]):
    """
    Module for testing ShaderToy fragment shader snippets.
    
    This module provides common ShaderToy uniforms:
    - iTime: Current time in seconds
    - iResolution: Viewport resolution
    - iMouse: Mouse position and click state
    - iFrame: Frame number
    """

    metadata = {
        "name": "ShaderToyTester",
        "description": "Test ShaderToy fragment shader snippets with common uniforms",
        "parameters": {},
    }
    frag_shader_path = "shaders/shader-toy-tester.frag"

    def __init__(self, params: ShaderToyTesterParams = ShaderToyTesterParams()):
        super().__init__(params)
        self.frame_count = 0

    def render_data(self, t: float) -> dict[str, Any]:
        """Return shader path and uniforms for rendering."""
        self.frame_count += 1
        
        uniforms: ShaderToyTesterUniforms = {
            "iTime": t,
            "iResolution": (self.params.width, self.params.height),
            "iMouse": (0.5, 0.5, 0.0, 0.0),  # Default mouse position
            "iFrame": self.frame_count,
        }
        
        return {
            "frag_shader_path": self.frag_shader_path,
            "uniforms": uniforms,
        }


if __name__ == "__main__":
    tester = ShaderToyTesterModule()
    print("Initial render data:", tester.render_data(0.0))
    print("After 1 second:", tester.render_data(1.0)) 