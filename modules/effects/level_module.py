from dataclasses import dataclass, field
from typing import Tuple

import moderngl

from core.registry import oblique_module
from modules.core.base_av_module import BaseAVModule, BaseAVParams, ParamBool, ParamFloat, Uniforms


@dataclass(kw_only=True)
class LevelParams(BaseAVParams):
    """
    Parameters for the Level module.
    
    Attributes:
        parent_module (BaseAVModule): Parent module providing the input texture.
        invert (bool): Invert colors (black↔white, red↔cyan, etc.)
        black_level (float): Clamp pixels with luminance <= this value to black (0.0-1.0)
        brightness (float): Add/subtract offset to RGB channels (-1.0 to 1.0)
        gamma (float): Gamma correction for non-linear brightness adjustment (0.1-3.0 typical)
        contrast (float): Scale factor for RGB channels around mid-gray (0.5-2.0 typical)
        opacity (float): Alpha channel adjustment (0.0-1.0)
    """
    parent_module: BaseAVModule = field(
        metadata={
            "description": "Source module whose output texture is level-adjusted.",
        }
    )
    # Pre-processing operations
    invert: ParamBool = field(
        default=False,
        metadata={
            "description": "Invert output colors after other level operations.",
        },
    )
    black_level: ParamFloat = field(
        default=0.0,
        metadata={
            "min": 0.0,
            "max": 1.0,
            "description": "Luminance threshold below which pixels are clamped to black.",
        },
    )
    brightness: ParamFloat = field(
        default=0.0,
        metadata={
            "min": -1.0,
            "max": 1.0,
            "description": "Linear RGB offset added after contrast.",
        },
    )
    gamma: ParamFloat = field(
        default=1.0,
        metadata={
            "min": 0.1,
            "max": 4.0,
            "description": "Gamma correction factor (1.0 leaves gamma unchanged).",
        },
    )
    contrast: ParamFloat = field(
        default=1.0,
        metadata={
            "min": 0.0,
            "max": 4.0,
            "description": "Contrast multiplier around mid-gray.",
        },
    )

    # Post-processing
    opacity: ParamFloat = field(
        default=1.0,
        metadata={
            "min": 0.0,
            "max": 1.0,
            "description": "Final alpha multiplier.",
        },
    )



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


@oblique_module(
    category="effects",
    description="Applies level controls such as brightness, contrast, and gamma.",
    tags=["clean", "composite", "transform", "muted"],
    cost_hint="low",
)
class LevelModule(BaseAVModule[LevelParams, LevelUniforms]):
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
    frag_shader_path: str = "modules/effects/shaders/level-module.frag"

    def __init__(self, params: LevelParams):
        """
        Initialize Level module.

        Args:
            params (LevelParams): Parameters for the level adjustments
            parent_module (BaseAVModule): Parent module to apply level adjustments to
        """
        super().__init__(params)

    def prepare_uniforms(self, t: float) -> LevelUniforms:
        """
        Return uniforms for level adjustments.

        Args:
            t (float): Current time

        Returns:
            Uniforms: Uniform values to pass to the shader
        """
        uniforms: LevelUniforms = {
            "u_time": t,
            "u_resolution": (self._resolve_param(self.params.width), self._resolve_param(self.params.height)),
            "u_texture": self.params.parent_module,
            "u_invert": 1.0 if self._resolve_param(self.params.invert) else 0.0,
            "u_black_level": self._resolve_param(self.params.black_level),
            "u_brightness": self._resolve_param(self.params.brightness),
            "u_gamma": self._resolve_param(self.params.gamma),
            "u_contrast": self._resolve_param(self.params.contrast),
            "u_opacity": self._resolve_param(self.params.opacity),
        }

        return uniforms
