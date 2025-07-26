"""
BrokenCirclesModule: Generates 5 concentric circles, each responding to a different input audio amplitude.
"""
from dataclasses import dataclass
from typing import List, Tuple

from core.logger import debug
from modules.base_av_module import BaseAVModule, BaseAVParams, RenderData, Uniforms
from processing.base_processing_operator import BaseProcessingOperator

# Metadata for the module
metadata = {
    "name": "BrokenCirclesModule",
    "description": "Generates 5 concentric circles that each respond to a different input audio amplitude.",
    "parameters": {
        "width": int,
        "height": int,
        "amplitudes": list,
    },
}

@dataclass(kw_only=True)
class BrokenCirclesParams(BaseAVParams):
    modulators: List[BaseProcessingOperator[float]]  # List of 5 modulation operators, one for each circle. Must be 5.

class BrokenCirclesUniforms(Uniforms, total=True):
    u_resolution: Tuple[int, int]
    u_amplitudes: List[float]
    u_time: float

class BrokenCirclesModule(BaseAVModule[BrokenCirclesParams]):
    """
    AV module that draws 5 concentric circles, each modulated by a different audio amplitude.
    """
    metadata = {
        "name": "BrokenCirclesModule",
        "description": "Generates 5 concentric circles, each modulated by a different audio amplitude.",
        "parameters": BrokenCirclesParams.__annotations__,
    }
    frag_shader_path: str = "shaders/broken-circles.frag"

    def __init__(self, params: BrokenCirclesParams):
        assert len(params.modulators) == 5, "Expected 5 circles modulation operators"
        super().__init__(params)
        self.params = params

    def render_data(self, t: float) -> RenderData:
        """
        Prepare parameters for the shader.
        Returns:
            Dictionary of uniforms for the shader.
        """
        amplitudes = [modulator.process() for modulator in self.params.modulators]
        return RenderData(
            frag_shader_path=self.frag_shader_path,
            uniforms=BrokenCirclesUniforms(
                u_resolution=(self.params.width, self.params.height),
                u_amplitudes=amplitudes,
                u_time=t,
            ),
        )
