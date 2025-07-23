from dataclasses import dataclass

from processing.base_processing_operator import BaseProcessingOperator

from .base_av_module import BaseAVModule, BaseAVParams, RenderData, Uniforms


@dataclass
class PauricSquaresParams(BaseAVParams):
    """Parameters for the Pauric Squares module."""
    tile_size: int = 8

class PauricSquaresUniforms(Uniforms, total=True):
    u_resolution: tuple[int, int]
    u_time: float
    u_tile_size: int

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
        params: PauricSquaresParams = PauricSquaresParams(),
    ):
        super().__init__(params)

    def render_data(self, t: float) -> RenderData:
        """
        Return shader path and uniforms for rendering.

        Args:
            t (float): Current time in seconds

        Returns:
            RenderData: Shader data and uniforms
        """
        return RenderData(
            frag_shader_path=self.frag_shader_path,
            uniforms=PauricSquaresUniforms(
                u_resolution=(self.params.width, self.params.height),
                u_time=t,
                u_tile_size=self.params.tile_size,
            ),
        )
