from dataclasses import dataclass

from processing.base_processing_operator import BaseProcessingOperator

from .base_av_module import BaseAVModule, BaseAVParams, RenderData, Uniforms


@dataclass
class DebugParams(BaseAVParams):
    number: float = 0.0
    width: int = 800
    height: int = 600

class DebugUniforms(Uniforms, total=True):
    u_number: float


class DebugModule(BaseAVModule[DebugParams]):
    """
    Debug module that displays an input number and string using a shader.
    """

    metadata = {
        "name": "DebugModule",
        "description": "Displays an input number and string for debugging purposes.",
        "parameters": {"number": float, "text": str},
    }
    frag_shader_path = "shaders/debug.frag"

    def __init__(
        self,
        params: DebugParams = DebugParams(),
        number_input: BaseProcessingOperator | None = None,
    ):
        super().__init__(params, number_input)
        self.number_input = number_input

    def prepare_uniforms(self, t: float) -> RenderData:
        # Return shader path and uniforms for rendering
        if self.number_input:
            number = self.number_input.process()
        else:
            number = self.params.number
        return RenderData(
            frag_shader_path=self.frag_shader_path,
            uniforms=DebugUniforms(
                u_number=number,
                u_resolution=(self.params.width, self.params.height)
            ),
        )
