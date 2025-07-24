from dataclasses import dataclass

import moderngl

from .base_av_module import BaseAVModule, BaseAVParams, RenderData, Uniforms


@dataclass
class PauricSquaresParams(BaseAVParams):
    """Parameters for the Pauric Squares module."""
    tile_size: int = 8

class PauricSquaresUniforms(Uniforms, total=True):
    u_resolution: tuple[int, int]
    u_time: float
    u_tile_size: int
    u_texture: moderngl.Texture

class PauricSquaresModule(BaseAVModule[PauricSquaresParams]):
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
        params: PauricSquaresParams,
        motif_module: BaseAVModule
    ):
        super().__init__(params)
        self.motif_module = motif_module

    def render_data(self, t: float) -> RenderData:
        """
        Return shader path and uniforms for rendering.

        Args:
            t (float): Current time in seconds

        Returns:
            RenderData: Shader data and uniforms
        """
        assert self.motif_texture is not None, "Motif texture not set, call render_texture first"
        return RenderData(
            frag_shader_path=self.frag_shader_path,
            uniforms=PauricSquaresUniforms(
                u_resolution=(self.params.width, self.params.height),
                u_time=t,
                u_tile_size=self.params.tile_size,
                u_texture=self.motif_texture,
            ),
        )

    def render_texture(self, ctx: moderngl.Context, width: int, height: int, t: float, filter=moderngl.NEAREST) -> moderngl.Texture:
        self.motif_texture = self.motif_module.render_texture(ctx, width, height, t, filter)
        return super().render_texture(ctx, width, height, t, filter)
