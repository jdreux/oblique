from .base_av_module import BaseAVModule, BaseAVParams
from typing import Any, Dict, Literal, Optional
from dataclasses import dataclass
import moderngl
from core.oblique_node import ObliqueNode
from processing.base_processing_operator import BaseProcessingOperator

@dataclass
class IkedaTestPatternParams(BaseAVParams):
    """Parameters for the Ikeda test pattern module."""
    speed_scale: float = 1.0
    pattern_intensity: float = 1.0
    distortion_amount: float = 0.3
    base_speed: float = 0.5
    width: int = 800
    height: int = 600

class IkedaTestPatternModule(BaseAVModule[IkedaTestPatternParams]):
    """
    Ikeda Test Pattern module that generates animated test patterns based on ShaderToy logic.
    
    Features:
    - Animated test pattern generation
    - Texture input support (upstream texture as tex0)
    - Configurable speed and intensity
    - GPU-accelerated pattern generation
    - Based on Ikeda-inspired visual patterns
    """
    metadata = {
        "name": "IkedaTestPatternModule",
        "description": "Generates animated Ikeda-inspired test patterns with texture input support.",
        "parameters": {
            "speed_scale": float,
            "pattern_intensity": float,
            "distortion_amount": float,
            "base_speed": float
        }
    }
    frag_shader_path = "shaders/ikeda-test-pattern.frag"

    def __init__(self, params: IkedaTestPatternParams, module: BaseAVModule):
        super().__init__(params)
        self.module = module


    def render_data(self, t: float) -> dict[str, Any]:
        """
        Return shader path and uniforms for rendering.
        
        Args:
            t (float): Current time in seconds
            
        Returns:
            dict[str, Any]: Shader data and uniforms
        """
        uniforms = {
            "u_resolution": (self.params.width, self.params.height),
            "u_time": t * self.params.speed_scale,
            "u_pattern_intensity": self.params.pattern_intensity,
            "u_distortion_amount": self.params.distortion_amount,
            "u_base_speed": self.params.base_speed
        }
        
        # Add input texture if available
        if self._upstream_tex is not None:
            uniforms["tex0"] = self._upstream_tex
        
        return {
            "frag_shader_path": self.frag_shader_path,
            "uniforms": uniforms
        }

    def render_texture(self, ctx: moderngl.Context, width: int, height: int, t: float, filter=moderngl.NEAREST) -> moderngl.Texture:
        self._upstream_tex = self.module.render_texture(ctx, width, height, t);

        # Render the module to a texture
        return super().render_texture(ctx, width, height, t)

if __name__ == "__main__":
    # Test the module
    params = IkedaTestPatternParams(
        speed_scale=1.0,
        pattern_intensity=1.0,
        distortion_amount=0.3,
        base_speed=0.5,
        width=800,
        height=600
    )
    