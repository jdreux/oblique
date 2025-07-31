from dataclasses import dataclass

import moderngl

from .base_av_module import BaseAVModule, BaseAVParams, ParamInt, Uniforms, ParamTexture


@dataclass
class PauricSquaresParams(BaseAVParams):
    """Parameters for the Pauric Squares module."""
    motif_texture: ParamTexture
    tile_size: ParamInt = 8

class PauricSquaresUniforms(Uniforms, total=True):
    u_resolution: tuple[int, int]
    u_time: float
    u_tile_size: int
    u_texture: BaseAVModule

class PauricSquaresModule(BaseAVModule[PauricSquaresParams, PauricSquaresUniforms]):
    """
    Pauric Squares module that generates animated square patterns in the style of Pauric Freeman.
    """

    metadata = {
        "name": "PauricSquaresModule",
        "description": "Generates animated square patterns with configurable size and color modes.",
        "parameters": PauricSquaresParams.__annotations__,
    }
    frag_shader_path = "shaders/pauric-squares.frag"

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
        assert self.motif_texture is not None, "Motif texture not set, call render_texture first"
        return PauricSquaresUniforms(
            u_resolution=(self._resolve_param(self.params.width), self._resolve_param(self.params.height)),
            u_time=t,
            u_tile_size=self._resolve_param(self.params.tile_size),
            u_texture=self.params.motif_texture,
        )
