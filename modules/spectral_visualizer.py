from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

from core.logger import debug
from modules.base_av_module import BaseAVModule, BaseAVParams, Uniforms
from processing.fft_bands import FFTBands

SHADER_BANDS_SIZE = 512


@dataclass
class SpectralVisualizerParams(BaseAVParams):
    num_bands: int = SHADER_BANDS_SIZE
    width: int = 800
    height: int = 600


class SpectralVisualizerUniforms(Uniforms, total=True):
    u_time: float
    u_resolution: Tuple[int, int]
    u_bands: List[float]
    u_num_bands: int


class SpectralVisualizerModule(BaseAVModule[SpectralVisualizerParams]):
    """
    SpectralVisualizer - Renders a frequency spectrum visualizer using FFT band data.
    Each bar represents a frequency band, colored by frequency.
    """

    metadata = {
        "name": "SpectralVisualizer",
        "description": "Renders a frequency spectrum visualizer with color mapping.",
        "parameters": SpectralVisualizerParams.__annotations__,
    }
    frag_shader_path: str = "shaders/spectral-visualizer.frag"

    def __init__(
        self,
        params: SpectralVisualizerParams = SpectralVisualizerParams(),
        band_levels_processor: Optional[FFTBands] = None,
    ):
        super().__init__(params)
        self.bands: List[float] = [0.0] * SHADER_BANDS_SIZE
        self.band_levels_processor = band_levels_processor

    def set_bands(self, bands: List[float]) -> None:
        if len(bands) < SHADER_BANDS_SIZE:
            self.bands = bands + [0.0] * (SHADER_BANDS_SIZE - len(bands))
        elif len(bands) > SHADER_BANDS_SIZE:
            self.bands = bands[:SHADER_BANDS_SIZE]
        else:
            self.bands = bands.copy()

    def render_data(self, t: float) -> dict[str, Any]:
        if self.band_levels_processor is not None:
            processor_bands = self.band_levels_processor.process()
            self.set_bands(list(processor_bands))
        uniforms: SpectralVisualizerUniforms = {
            "u_time": t,
            "u_resolution": (self.params.width, self.params.height),
            "u_bands": self.bands,
            "u_num_bands": self.params.num_bands,
        }
        return {
            "frag_shader_path": self.frag_shader_path,
            "uniforms": uniforms,
        }
