from dataclasses import dataclass
from typing import Tuple

from modules.base_av_module import BaseAVModule, BaseAVParams, Uniforms
from processing.fft_bands import FFTBands


@dataclass
class CircleEchoParams(BaseAVParams):
    n_circles: int = 8
    mod_depth: float = 0.8
    audio_level: float = 0.0


class CircleEchoUniforms(Uniforms, total=True):
    u_n_circles: int
    u_mod_depth: float
    u_audio_level: float
    u_band_amps: Tuple[float, ...]


class CircleEcho(BaseAVModule[CircleEchoParams, CircleEchoUniforms]):
    """
    CircleEcho - Concentric modulated circles.
    """

    metadata = {
        "name": "CircleEcho",
        "description": "Concentric modulated circles.",
        "parameters": CircleEchoParams.__annotations__,
    }
    frag_shader_path: str = "shaders/circle-echo.frag"

    def __init__(
        self, params: CircleEchoParams, band_levels_processor: FFTBands
    ):
        """
        Initialize CircleEcho module.
        Args:
            params (CircleEchoParams): Parameters for the module.
            band_levels_processor (Optional[FFTBands]): Optional processor for band amplitudes.
        """
        super().__init__(params)
        self.band_levels_processor = band_levels_processor

    def prepare_uniforms(self, t: float) -> CircleEchoUniforms:
        uniforms: CircleEchoUniforms = {
            "u_resolution": (self.params.width, self.params.height),
            "u_n_circles": self.params.n_circles,
            "u_mod_depth": self.params.mod_depth,
            "u_audio_level": self.params.audio_level,
            "u_band_amps": tuple(self.band_levels_processor.process())
        }
        return uniforms
