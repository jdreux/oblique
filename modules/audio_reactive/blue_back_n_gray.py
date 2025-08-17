from dataclasses import dataclass

from modules.core.base_av_module import BaseAVModule, BaseAVParams, ParamFloat, ParamInt, TexturePass, Uniforms


@dataclass
class BlueBackNGrayParams(BaseAVParams):
    n_circles: ParamInt = 8
    mod_depth: ParamFloat = 0.6
    audio_level: ParamFloat = 0.0
    strip_offset: ParamFloat = 3.0  # pixels offset for strips


class BlueBackNGrayUniforms(Uniforms, total=True):
    u_time: float
    u_strip_offset: float
    u_circles_texture: object  # The texture from the circles pass


class BlueBackNGrayModule(BaseAVModule[BlueBackNGrayParams, BlueBackNGrayUniforms]):
    """
    BlueBackNGray - Concentric circles with gray edges on white background and vertical strips offset effect.
    """

    metadata = {
        "name": "BlueBackNGray",
        "description": "Concentric circles with gray edges and vertical strips offset effect",
        "parameters": BlueBackNGrayParams.__annotations__,
    }
    frag_shader_path: str = "modules/audio_reactive/shaders/blue-back-n-gray-final.frag"

    circles_pass = TexturePass(
        frag_shader_path="modules/audio_reactive/shaders/blue-back-n-gray-circles.frag",
        uniforms={},  # Will be populated in prepare_uniforms
        name="circles_background"
    )

    def __init__(self, params: BlueBackNGrayParams):
        """
        Initialize BlueBackNGray module with TexturePass architecture.
        """
        super().__init__(params)

    def prepare_uniforms(self, t: float) -> BlueBackNGrayUniforms:
        # Update the circles pass uniforms with resolved values
        self.circles_pass.uniforms = {
            "n_circles": self._resolve_param(self.params.n_circles),
            "mod_depth": self._resolve_param(self.params.mod_depth),
            "audio_level": self._resolve_param(self.params.audio_level),
        }

        uniforms: BlueBackNGrayUniforms = BlueBackNGrayUniforms(
            u_resolution=self._resolve_resolution(),
            u_time=t,
            u_strip_offset=self._resolve_param(self.params.strip_offset),
            u_circles_texture=self.circles_pass,
        )
        return uniforms
