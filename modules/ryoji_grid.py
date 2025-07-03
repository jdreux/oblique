from dataclasses import dataclass
from typing import Any
from typing import TypedDict, Tuple
from modules.base_av_module import BaseAVModule, Uniforms, BaseAVParams

@dataclass
class RyojiGridParams(BaseAVParams):
    pass

class RyojiGridUniforms(Uniforms, total=True):
    u_time: float
    u_resolution: Tuple[int, int]

class RyojiGrid(BaseAVModule[RyojiGridParams]):
    """
    RyojiGrid - Minimal grid animation inspired by Ryoji Ikeda.
    This module generates a simple animated grid using a GLSL shader.
    The render method returns the data needed for the renderer.
    """
    metadata = {
        'name': 'RyojiGrid',
        'description': 'Minimal grid animation inspired by Ryoji Ikeda.',
        'parameters': RyojiGridParams.__annotations__,
    }
    frag_shader_path: str = 'shaders/ryoji-grid.frag'

    def __init__(self, params: RyojiGridParams = RyojiGridParams()):
        super().__init__(params)
        self.width = self.params.width
        self.height = self.params.height

    def update(self, params: RyojiGridParams) -> None:
        self.params = params
        self.width = self.params.width
        self.height = self.params.height

    def render(self, t: float) -> dict[str, Any]:
        """
        Return the data needed for the renderer to render this module.
        """
        uniforms: RyojiGridUniforms = {
            'u_time': t,
            'u_resolution': (self.width, self.height),
        }
        return {
            'frag_shader_path': self.frag_shader_path,
            'uniforms': uniforms,
        }

if __name__ == "__main__":
    params = RyojiGridParams(width=800, height=600)
    grid = RyojiGrid(params)
    grid.update(params)