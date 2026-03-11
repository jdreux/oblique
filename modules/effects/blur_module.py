from dataclasses import dataclass, field

import moderngl

from core.registry import oblique_module
from modules.core.base_av_module import BaseAVModule, BaseAVParams, ParamFloat, ParamInt, ParamTexture, Uniforms


@dataclass
class BlurParams(BaseAVParams):
    """Parameters for the Blur module."""
    input_texture: ParamTexture = field(
        metadata={
            "description": "Input texture to blur.",
        }
    )
    blur_amount: ParamFloat = field(
        default=10.0,
        metadata={
            "min": 0.0,
            "max": 128.0,
            "description": "Blur radius in pixels (module-level control).",
        },
    )
    kernel_size: ParamInt = field(
        default=5,
        metadata={
            "min": 1,
            "max": 64,
            "description": "Gaussian kernel radius/size used by the blur shader.",
        },
    )


class BlurUniforms(Uniforms, total=True):
    u_time: float
    u_resolution: tuple[int, int]
    u_kernel_size: int
    u_input_texture: moderngl.Texture


@oblique_module(
    category="effects",
    description="Applies Gaussian blur to upstream textures with configurable kernel size.",
    tags=["blur", "muted", "organic"],
    cost_hint="medium",
)
class BlurModule(BaseAVModule[BlurParams, BlurUniforms]):
    """
    Blur module that applies Gaussian blur to input textures using Lygia's gaussianBlur function.
    
    The module takes an input texture and applies configurable Gaussian blur with
    adjustable amount, direction, and kernel size for various blur effects.
    """

    metadata = {
        "name": "BlurModule",
        "description": "Applies Gaussian blur to input textures with configurable parameters.",
        "parameters": BlurParams.__annotations__,
    }
    frag_shader_path: str = "modules/effects/shaders/blur-module.frag"

    def __init__(self, params: BlurParams):
        super().__init__(params)
        self.width = self.params.width
        self.height = self.params.height

    def prepare_uniforms(self, t: float) -> BlurUniforms:
        """
        Return the uniforms needed for rendering.
        """

        uniforms: BlurUniforms = {
            "u_time": t,
            "u_resolution": self._resolve_resolution(),
            "u_kernel_size": self._resolve_param(self.params.kernel_size),
            "u_input_texture": self.params.input_texture,
        }

        return uniforms
