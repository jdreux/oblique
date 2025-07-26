from dataclasses import dataclass

import moderngl

from modules.base_av_module import BaseAVModule, BaseAVParams, ParamFloat, ParamInt, ParamTexture, RenderData, Uniforms


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
    u_input_texture: moderngl.Texture | None


class BlurModule(BaseAVModule[BlurParams]):
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
    frag_shader_path: str = "shaders/blur-module.frag"

    def __init__(self, params: BlurParams):
        super().__init__(params)
        self.width = self.params.width
        self.height = self.params.height

    def prepare_uniforms(self, t: float) -> RenderData:
        """
        Return the data needed for the renderer to render this module.
        """

        uniforms: BlurUniforms = {
            "u_time": t,
            "u_resolution": self._resolve_resolution(),
            "u_kernel_size": self._resolve_param(self.params.kernel_size),
            "u_input_texture": self.input_tex,  # Will be set in render_texture
        }

        return RenderData(
            frag_shader_path=self.frag_shader_path,
            uniforms=uniforms,
        )

    def render_texture(
        self,
        ctx: moderngl.Context,
        width: int,
        height: int,
        t: float,
        filter=moderngl.NEAREST,
    ) -> moderngl.Texture:
        """
        Override render_texture to handle input texture from input module.
        """

        self.input_tex = self._resolve_texture_param(self.params.input_texture, ctx, width, height, t, filter)
        # Render the module to a texture
        return super().render_texture(ctx, width, height, t)
