from typing import Any, List, Tuple
from modules.base_av_module import BaseAVModule, Uniforms, BaseAVParams
from processing.fft_bands import FFTBands
from processing.normalized_amplitude import NormalizedAmplitudeOperator


class MeshShroudParams(BaseAVParams):
    width: int = 800
    height: int = 600

class MeshShroudUniforms(Uniforms, total=True):
    u_time: float
    u_resolution: Tuple[int, int]
    u_fft_bands: List[float]
    u_amp: float



class MeshShroudModule(BaseAVModule[MeshShroudParams]):
    """
    MeshShroudModule - Renders a floating mesh spectrum visualizer using FFT band data.
    """

    metadata = {
        "name": "MeshShroudModule",
        "description": "Renders a frequency spectrum visualizer with mesh animation.",
        "parameters": MeshShroudParams.__annotations__,
    }
    frag_shader_path = "shaders/mesh-shroud.frag"

    def __init__(
        self,
        params: MeshShroudParams,
        band_levels_processor: FFTBands,
        amplitude_processor: NormalizedAmplitudeOperator
    ):
        super().__init__(params)
        self.width = self.params.width
        self.height = self.params.height
        self.band_levels_processor = band_levels_processor
        self.amplitude_processor = amplitude_processor


    def render_data(self, t: float) -> dict[str, Any]:
        uniforms: MeshShroudUniforms = {
            "u_time": t,
            "u_resolution": (self.params.width, self.params.height),
            "u_fft_bands": self.band_levels_processor.process(),
            "u_amp": self.amplitude_processor.process()
        }
        return {"frag_shader_path": self.frag_shader_path,
                "uniforms": uniforms}
