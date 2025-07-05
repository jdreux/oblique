from .base_av_module import BaseAVModule, BaseAVParams
from typing import Any, Dict, Literal
from dataclasses import dataclass
import numpy as np
from core.oblique_node import ObliqueNode
from processing.base_processing_operator import BaseProcessingOperator

@dataclass
class VisualNoiseParams(BaseAVParams):
    """Parameters for the visual noise module."""
    noise_size: Literal["small", "medium", "large"] = "medium"
    color_mode: Literal["gray", "rgba"] = "gray"
    intensity: float = 1.0
    speed: float = 1.0
    width: int = 800
    height: int = 600

class VisualNoiseModule(BaseAVModule[VisualNoiseParams]):
    """
    Visual noise module that generates different types of noise patterns.
    
    Features:
    - Three noise sizes: small, medium, large
    - Two color modes: gray (monochrome) or RGBA (colorful)
    - Adjustable intensity and animation speed
    - GPU-accelerated noise generation
    """
    metadata = {
        "name": "VisualNoiseModule",
        "description": "Generates visual noise patterns with configurable size and color modes.",
        "parameters": {
            "noise_size": "small|medium|large",
            "color_mode": "gray|rgba", 
            "intensity": float,
            "speed": float
        }
    }
    frag_shader_path = "shaders/visual-noise.frag"

    def __init__(self, params: VisualNoiseParams = VisualNoiseParams(), parent: BaseProcessingOperator | None = None):
        super().__init__(params, parent)
        self.parent = parent

    def render_data(self, t: float) -> dict[str, Any]:
        """
        Return shader path and uniforms for rendering.
        
        Args:
            t (float): Current time in seconds
            
        Returns:
            dict[str, Any]: Shader data and uniforms
        """
        # Map noise size to scale factor
        size_scale = {
            "small": 1,
            "medium": 500,
            "large": 10000
        }
        
        # Map color mode to shader flag
        color_mode_flag = 1.0 if self.params.color_mode == "rgba" else 0.0
        
        return {
            "frag_shader_path": self.frag_shader_path,
            "uniforms": {
                "u_resolution": (self.params.width, self.params.height),
                "u_time": t * self.params.speed,
                "u_noise_scale": size_scale[self.params.noise_size],
                "u_intensity": self.params.intensity,
                "u_color_mode": color_mode_flag
            }
        }

if __name__ == "__main__":
    # Test the module
    params = VisualNoiseParams(
        noise_size="medium",
        color_mode="rgba",
        intensity=0.8,
        speed=2.0,
        width=800,
        height=600
    )
    
    noise_module = VisualNoiseModule(params)
    print("Visual Noise Module created successfully!")
    print(f"Parameters: {params}")
    print("Initial render data:", noise_module.render_data(0.0)) 