from dataclasses import dataclass

import moderngl

from modules.core.base_av_module import BaseAVModule, BaseAVParams, ParamFloat, ParamInt, ParamTexture, Uniforms


@dataclass
class BlurParams(BaseAVParams):
    """Parameters for the Blur module."""
    input_texture: ParamTexture  # Input texture to blur
    blur_amount: ParamFloat = 10.0  # Blur strength (pixels)
    kernel_size: ParamInt = 5  # Kernel size: larger is more blur but slower. Recommend 5-20


class BlurUniforms(Uniforms, total=True):
    u_time: float
    u_resolution: tuple[int, int]
    u_kernel_size: int
    u_input_texture: BaseAVModule


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
