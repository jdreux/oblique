from dataclasses import dataclass, field

from core.registry import oblique_module
from modules.core.base_av_module import BaseAVModule, BaseAVParams, ParamFloat, ParamInt, TexturePass, Uniforms


@dataclass
class BlueBackNGrayParams(BaseAVParams):
    n_circles: ParamInt = field(
        default=8,
        metadata={
            "min": 1,
            "max": 16,
            "description": "Number of concentric circles in the source pass.",
        },
    )
    mod_depth: ParamFloat = field(
        default=0.6,
        metadata={
            "min": 0.0,
            "max": 1.0,
            "description": "Audio-driven radius modulation depth for circles.",
        },
    )
    audio_level: ParamFloat = field(
        default=0.0,
        metadata={
            "min": 0.0,
            "max": 1.0,
            "description": "Global audio level multiplier for circle animation.",
        },
    )
    strip_offset: ParamFloat = field(
        default=3.0,
        metadata={
            "min": 0.0,
            "max": 200.0,
            "description": "Vertical strip displacement in pixels for the final pass.",
        },
    )


class BlueBackNGrayUniforms(Uniforms, total=True):
    u_time: float
    u_strip_offset: float
    u_circles_texture: object  # The texture from the circles pass


@oblique_module(
    category="audio_reactive",
    description="Renders concentric circles with strip-offset post processing.",
    tags=["geometric", "audio-reactive", "minimal", "monochrome"],
    cost_hint="medium",
)
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
            "u_n_circles": self._resolve_param(self.params.n_circles),
            "u_mod_depth": self._resolve_param(self.params.mod_depth),
            "u_audio_level": self._resolve_param(self.params.audio_level),
        }

        uniforms: BlueBackNGrayUniforms = BlueBackNGrayUniforms(
            u_resolution=self._resolve_resolution(),
            u_time=t,
            u_strip_offset=self._resolve_param(self.params.strip_offset),
            u_circles_texture=self.circles_pass,
        )
        return uniforms
