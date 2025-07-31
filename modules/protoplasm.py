from dataclasses import dataclass

import moderngl

from .base_av_module import (
    BaseAVModule,
    BaseAVParams,
    ParamFloat,
    ParamTexture,
    RenderData,
    Uniforms,
    OffscreenTexturePass,
)


@dataclass
class ProtoplasmParams(BaseAVParams):
    """Parameters for the Protoplasm module."""


class ProtoplasmUniforms(Uniforms, total=True):
    u_time: float
    u_texture: moderngl.Texture


class ProtoplasmModule(BaseAVModule[ProtoplasmParams]):
    """
    Protoplasm module that generates organic, volumetric patterns using ray marching and FBM noise.

    Features:
    - Organic, fluid-like volumetric patterns
    - Ray marched 3D space with procedural noise
    - Audio-reactive modulation
    - GPU-accelerated pattern generation using GLSL
    - Based on a classic ShaderToy effect, adapted for Oblique
    """

    metadata = {
        "name": "ProtoplasmModule",
        "description": "Generates organic, audio-reactive volumetric patterns using ray marching and FBM noise.",
        "parameters": {
            "noise_texture": "ParamTexture",
            "speed": "float",
        },
    }
    frag_shader_path = "shaders/protoplasm.frag"

    offscreen_passes = {
        "noise_texture": OffscreenTexturePass(
            frag_shader_path="shaders/noise.frag",
        )
    }

    def __init__(self, params: ProtoplasmParams):
        super().__init__(params)

    def prepare_uniforms(self, t: float) -> RenderData:
        """
        Return shader path and uniforms for rendering.

        Args:
            t (float): Current time in seconds

        Returns:
            RenderData: Shader data and uniforms
        """
        uniforms: ProtoplasmUniforms = {
            "u_resolution": self._resolve_resolution(),
            "u_time": t,
            # "u_noise_texture": self.offscreen_passes["noise_texture"].texture
        }

        return RenderData(
            frag_shader_path=self.frag_shader_path,
            uniforms=uniforms,
        )