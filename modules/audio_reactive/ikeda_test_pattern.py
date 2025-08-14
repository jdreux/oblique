from dataclasses import dataclass

from modules.core.base_av_module import (
    BaseAVModule,
    BaseAVParams,
    TexturePass,
    Uniforms,
)


@dataclass
class IkedaTestPatternParams(BaseAVParams):
    """Parameters for the Ikeda Test Pattern module."""


class IkedaTestPatternUniforms(Uniforms, total=True):
    u_time: float
    u_noise_texture: TexturePass

debug_texture: TexturePass = TexturePass(
    frag_shader_path="modules/utility/shaders/debug.frag",
)

class IkedaTestPatternModule(BaseAVModule[IkedaTestPatternParams, IkedaTestPatternUniforms]):
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
    frag_shader_path = "modules/audio_reactive/shaders/ikeda-test-pattern.frag"

    debug_texture: TexturePass = debug_texture

    noise_texture: TexturePass = TexturePass(
        frag_shader_path="modules/core/shaders/noise.frag",
        uniforms={"u_debug_texture": debug_texture}
    )

    def __init__(self, params: IkedaTestPatternParams):
        super().__init__(params)

    def prepare_uniforms(self, t: float) -> IkedaTestPatternUniforms:
        """
        Return uniforms for rendering.

        Args:
            t (float): Current time in seconds

        Returns:
            Uniforms: Uniform values to pass to the shader
        """
        uniforms: IkedaTestPatternUniforms = {
            "u_resolution": self._resolve_resolution(),
            "u_time": t,
            "u_noise_texture": self.noise_texture
        }

        return uniforms
