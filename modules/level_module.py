from dataclasses import dataclass
from typing import Any, Tuple

import moderngl

from modules.base_av_module import BaseAVModule, BaseAVParams, Uniforms


@dataclass
class LevelParams(BaseAVParams):
    """
    Parameters for the Level module.
    
    Attributes:
        invert (bool): Invert colors (black↔white, red↔cyan, etc.)
        black_level (float): Clamp pixels with luminance <= this value to black (0.0-1.0)
        brightness (float): Add/subtract offset to RGB channels (-1.0 to 1.0)
        gamma (float): Gamma correction for non-linear brightness adjustment (0.1-3.0 typical)
        contrast (float): Scale factor for RGB channels around mid-gray (0.5-2.0 typical)
        opacity (float): Alpha channel adjustment (0.0-1.0)
    """
    # Pre-processing operations
    invert: bool = False
    black_level: float = 0.0  # Any pixel <= this becomes black
    brightness: float = 0.0  # Add/subtract offset to RGB (-1 to 1 range)
    gamma: float = 1.0  # Gamma correction (0.1 to 3.0 typical)
    contrast: float = 1.0  # Scale factor for RGB channels

    # Post-processing
    opacity: float = 1.0  # Alpha channel adjustment (0.0 to 1.0)


class LevelUniforms(Uniforms, total=True):
    """Uniforms for the Level module shader."""
    u_time: float
    u_resolution: Tuple[int, int]
    u_texture: moderngl.Texture
    u_invert: float  # 1.0 if invert enabled, 0.0 otherwise
    u_black_level: float
    u_brightness: float
    u_gamma: float
    u_contrast: float
    u_opacity: float


class LevelModule(BaseAVModule[LevelParams]):
    """
    Level module that applies level adjustments to input textures.
    
    This module implements:
    - Brightness adjustment (add/subtract offset)
    - Contrast adjustment (scale factor around mid-gray)
    - Gamma correction (non-linear brightness)
    - Color inversion (black↔white, red↔cyan, etc.)
    - Black level clamping (luminance-based)
    - Opacity adjustment
    
    Takes a parent module as input and applies level operations in real-time.
    All operations are performed in a single GPU pass for optimal performance.
    """

    metadata = {
        "name": "LevelModule",
        "description": "Applies level adjustments (brightness, contrast, gamma, invert, black level, opacity) to input textures.",
        "parameters": {
            "invert": "bool",
            "black_level": "float",
            "brightness": "float",
            "gamma": "float",
            "contrast": "float",
            "opacity": "float",
        },
    }
    frag_shader_path: str = "shaders/level-module.frag"

    def __init__(self, params: LevelParams, parent_module: BaseAVModule):
        """
        Initialize Level module.

        Args:
            params (LevelParams): Parameters for the level adjustments
            parent_module (BaseAVModule): Parent module to apply level adjustments to
        """
        super().__init__(params, parent_module)
        self.width = self.params.width
        self.height = self.params.height
        self.parent_module = parent_module

    def render_data(self, t: float) -> dict[str, Any]:
        """
        Return shader data with level adjustment uniforms.

        Args:
            t (float): Current time

        Returns:
            dict[str, Any]: Shader path and uniforms
        """
        uniforms: LevelUniforms = {
            "u_time": t,
            "u_resolution": (self.width, self.height),
            "u_texture": self.parent_tex,
            "u_invert": 1.0 if self.params.invert else 0.0,
            "u_black_level": self.params.black_level,
            "u_brightness": self.params.brightness,
            "u_gamma": self.params.gamma,
            "u_contrast": self.params.contrast,
            "u_opacity": self.params.opacity,
        }

        return {
            "frag_shader_path": self.frag_shader_path,
            "uniforms": uniforms,
        }

    def render_texture(
        self,
        ctx: moderngl.Context,
        width: int,
        height: int,
        t: float,
        filter=moderngl.NEAREST,
    ) -> moderngl.Texture:
        """
        Render the level module by first rendering the parent module to a texture,
        then applying the level adjustments using that texture as input.
        """
        # Render parent module to texture
        self.parent_tex = self.parent_module.render_texture(ctx, width, height, t, filter)

        # Render the level adjustments
        return super().render_texture(ctx, width, height, t, filter)