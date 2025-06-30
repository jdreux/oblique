from dataclasses import dataclass
from typing import Any
from modules.base_av_module import BaseAVModule

@dataclass
class RyojiGridParams:
    width: int = 800
    height: int = 600

class RyojiGrid(BaseAVModule):
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

    def __init__(self, props: RyojiGridParams = RyojiGridParams()):
        super().__init__(props)
        self.props = props
        self.width = self.props.width
        self.height = self.props.height

    def update(self, props: RyojiGridParams):
        self.props = props
        self.width = self.props.width
        self.height = self.props.height

    def render(self, t: float) -> dict[str, Any]:
        """
        Return the data needed for the renderer to render this module.
        """
        return {
            'frag_shader_path': 'shaders/ryoji-grid.frag',
            'uniforms': {
                'u_time': t,
                'u_resolution': (self.width, self.height),
            }
        }

if __name__ == "__main__":
    params = RyojiGridParams(width=800, height=600)
    grid = RyojiGrid(params)
    grid.update(params)