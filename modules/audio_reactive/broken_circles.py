"""
BrokenCirclesModule: Generates 5 concentric circles, each responding to a different input audio amplitude.
"""
from dataclasses import dataclass
from typing import List, Tuple

from core.logger import debug
from modules.base_av_module import BaseAVModule, BaseAVParams, Uniforms
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

class BrokenCirclesModule(BaseAVModule[BrokenCirclesParams, BrokenCirclesUniforms]):
    """
    AV module that draws 5 concentric circles, each modulated by a different audio amplitude.
    """
    metadata = {
        "name": "BrokenCirclesModule",
        "description": "Generates 5 concentric circles, each modulated by a different audio amplitude.",
        "parameters": BrokenCirclesParams.__annotations__,
    }
    frag_shader_path: str = "modules/audio_reactive/broken-circles.frag"

    def __init__(self, params: BrokenCirclesParams):
        assert len(params.modulators) == 5, "Expected 5 circles modulation operators"
        super().__init__(params)
        self.params = params

    def prepare_uniforms(self, t: float) -> BrokenCirclesUniforms:
        """
        Prepare parameters for the shader.
        Returns:
            Uniforms: Uniform values to pass to the shader.
        """
        amplitudes = [modulator.process() for modulator in self.params.modulators]
        return BrokenCirclesUniforms(
            u_resolution=(self._resolve_param(self.params.width), self._resolve_param(self.params.height)),
            u_amplitudes=amplitudes,
            u_time=t,
        )
