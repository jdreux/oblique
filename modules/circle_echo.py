from dataclasses import dataclass
from typing import Any, Tuple, Optional
from modules.base_av_module import BaseAVModule, Uniforms, BaseAVParams
from processing.fft_bands import FFTBands

@dataclass
class CircleEchoParams(BaseAVParams):
    n_circles: int = 8
    mod_depth: float = 0.8
    audio_level: float = 0.0
    band_amps: Tuple[float, ...] = (0.0,) * 16

class CircleEchoUniforms(Uniforms, total=True):
    u_time: float
    u_resolution: Tuple[int, int]
    u_n_circles: int
    u_mod_depth: float
    u_audio_level: float
    u_band_amps: Tuple[float, ...]

class CircleEcho(BaseAVModule[CircleEchoParams]):
    """
    CircleEcho - Concentric modulated circles.
    """
    metadata = {
        'name': 'CircleEcho',
        'description': 'Concentric modulated circles.',
        'parameters': CircleEchoParams.__annotations__,
    }
    frag_shader_path: str = 'shaders/circle-echo.frag'

    def __init__(self, params: CircleEchoParams, band_levels_processor: Optional[FFTBands] = None):
        """
        Initialize CircleEcho module.
        Args:
            params (CircleEchoParams): Parameters for the module.
            band_levels_processor (Optional[FFTBands]): Optional processor for band amplitudes.
        """
        super().__init__(params)
        self.width = self.params.width
        self.height = self.params.height
        self.n_circles = self.params.n_circles
        self.mod_depth = self.params.mod_depth
        self.audio_level = self.params.audio_level
        self.band_amps = tuple(self.params.band_amps)
        self.band_levels_processor = band_levels_processor

    def update(self, params: CircleEchoParams) -> None:
        self.params = params
        self.width = self.params.width
        self.height = self.params.height
        self.n_circles = self.params.n_circles
        self.mod_depth = self.params.mod_depth
        self.audio_level = self.params.audio_level
        self.band_amps = tuple(self.params.band_amps)

    def render(self, t: float) -> dict[str, Any]:
        if self.band_levels_processor:
            band_amps_list = self.band_levels_processor.process()
            self.band_amps = tuple(band_amps_list)
        uniforms: CircleEchoUniforms = {
            'u_time': t,
            'u_resolution': (self.width, self.height),
            'u_n_circles': self.n_circles,
            'u_mod_depth': self.mod_depth,
            'u_audio_level': self.audio_level,
            'u_band_amps': self.band_amps,
        }
        return {
            'frag_shader_path': self.frag_shader_path,
            'uniforms': uniforms,
        }

if __name__ == "__main__":
    params = CircleEchoParams(width=800, height=600, n_circles=8, mod_depth=0.08, audio_level=0.0)
    module = CircleEcho(params)
    module.update(params)
    print(module.render(0.0)) 