from typing import Tuple

from modules.base_av_module import BaseAVModule, BaseAVParams, ParamFloat, ParamFloatList, RenderData, Uniforms


class MeshShroudParams(BaseAVParams):
    amplitude: ParamFloat
    fft_bands: ParamFloatList

class MeshShroudUniforms(Uniforms, total=True):
    u_time: float
    u_resolution: Tuple[int, int]
    u_fft_bands: list[float]
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
    ):
        super().__init__(params)

    def prepare_uniforms(self, t: float) -> RenderData:
        uniforms: MeshShroudUniforms = {
            "u_time": t,
            "u_resolution": (self._resolve_param(self.params.width), self._resolve_param(self.params.height)),
            "u_fft_bands": self._resolve_param(self.params.fft_bands),
            "u_amp": self._resolve_param(self.params.amplitude)
        }
        return RenderData(
            frag_shader_path=self.frag_shader_path,
            uniforms=uniforms,
        )
