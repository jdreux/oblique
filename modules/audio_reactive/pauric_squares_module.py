from dataclasses import dataclass, field

import moderngl

from core.registry import oblique_module
from modules.core.base_av_module import BaseAVModule, BaseAVParams, ParamInt, Uniforms, ParamTexture


@dataclass
class PauricSquaresParams(BaseAVParams):
    """Parameters for the Pauric Squares module."""
    motif_texture: ParamTexture = field(
        metadata={
            "description": "Input motif texture sampled inside each tile cell.",
        }
    )
    tile_size: ParamInt = field(
        default=8,
        metadata={
            "min": 1,
            "max": 128,
            "description": "Tile grid density (cells per axis).",
        },
    )

class PauricSquaresUniforms(Uniforms, total=True):
    u_resolution: tuple[int, int]
    u_time: float
    u_tile_size: int
    u_texture: moderngl.Texture

@oblique_module(
    category="audio_reactive",
    description="Tiles a motif texture into animated, audio-reactive square patterns.",
    tags=["geometric", "audio-reactive", "minimal", "rhythmic"],
    cost_hint="medium",
)
class PauricSquaresModule(BaseAVModule[PauricSquaresParams, PauricSquaresUniforms]):
    """
    Pauric Squares module that generates animated square patterns in the style of Pauric Freeman.
    """

    metadata = {
        "name": "PauricSquaresModule",
        "description": "Generates animated square patterns with configurable size and color modes.",
        "parameters": PauricSquaresParams.__annotations__,
    }
    frag_shader_path = "modules/audio_reactive/shaders/pauric-squares.frag"

    def __init__(
        self,
        params: PauricSquaresParams
    ):
        super().__init__(params)

    def prepare_uniforms(self, t: float) -> PauricSquaresUniforms:
        """
        Return uniforms for rendering.

        Args:
            t (float): Current time in seconds

        Returns:
            Uniforms: Uniform values to pass to the shader
        """
        return PauricSquaresUniforms(
            u_resolution=(self._resolve_param(self.params.width), self._resolve_param(self.params.height)),
            u_time=t,
            u_tile_size=self._resolve_param(self.params.tile_size),
            u_texture=self.params.motif_texture,
        )
