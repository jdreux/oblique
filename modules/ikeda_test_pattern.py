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
class IkedaTestPatternParams(BaseAVParams):
    """Parameters for the Ikeda Test Pattern module."""


class IkedaTestPatternUniforms(Uniforms, total=True):
    u_time: float
    u_noise_texture: OffscreenTexturePass

debug_texture: OffscreenTexturePass = OffscreenTexturePass(
    frag_shader_path="shaders/debug.frag",
)

class IkedaTestPatternModule(BaseAVModule[IkedaTestPatternParams]):
    """
    Ikeda Test Pattern module that generates geometric patterns inspired by Ryoji Ikeda's work.

    Features:
    - High contrast black and white patterns
    - Grid-based geometric layouts
    - Glitch effects and pattern distortion
    - Configurable pattern scale and density
    - GPU-accelerated pattern generation
    """

    metadata = {
        "name": "IkedaTestPatternModule",
        "description": "Generates geometric test patterns inspired by Ryoji Ikeda's visual style.",
        "parameters": {
            "noise_texture": "ParamTexture",
            "speed": "float",
        },
    }
    frag_shader_path = "shaders/ikeda-test-pattern.frag"

    debug_texture: OffscreenTexturePass = debug_texture

    noise_texture: OffscreenTexturePass = OffscreenTexturePass(
        frag_shader_path="shaders/noise.frag",
        offscreen_inputs={"u_debug_texture": debug_texture}
    )

    def __init__(self, params: IkedaTestPatternParams):
        super().__init__(params)

    def prepare_uniforms(self, t: float) -> RenderData:
        """
        Return shader path and uniforms for rendering.

        Args:
            t (float): Current time in seconds

        Returns:
            RenderData: Shader data and uniforms
        """
        uniforms: IkedaTestPatternUniforms = {
            "u_resolution": self._resolve_resolution(),
            "u_time": t,
            "u_noise_texture": self.noise_texture
        }

        return RenderData(
            frag_shader_path=self.frag_shader_path,
            uniforms=uniforms,
        )