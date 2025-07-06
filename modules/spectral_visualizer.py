from dataclasses import dataclass
from typing import Any, List, Tuple, Optional
from modules.base_av_module import BaseAVModule, Uniforms, BaseAVParams
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
        'name': 'SpectralVisualizer',
        'description': 'Renders a frequency spectrum visualizer with color mapping.',
        'parameters': SpectralVisualizerParams.__annotations__,
    }
    frag_shader_path: str = 'shaders/spectral-visualizer.frag'

    def __init__(self, params: SpectralVisualizerParams = SpectralVisualizerParams(), band_levels_processor: Optional[FFTBands] = None):
        super().__init__(params)
        self.width = self.params.width
        self.height = self.params.height
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
            self.set_bands(processor_bands)
        uniforms: SpectralVisualizerUniforms = {
            'u_time': t,
            'u_resolution': (self.width, self.height),
            'u_bands': self.bands,
            'u_num_bands': self.params.num_bands,
        }
        return {
            'frag_shader_path': self.frag_shader_path,
            'uniforms': uniforms,
        }

if __name__ == "__main__":
    params = SpectralVisualizerParams(width=800, height=400, num_bands=512)
    vis = SpectralVisualizer(params)
    import numpy as np
    # Simulate a spectrum with a peak
    test_bands = np.abs(np.sin(np.linspace(0, 3.14, 512)))
    vis.set_bands(test_bands.tolist())
    result = vis.render_data(1.0)
    print(f"Render result: {result}") 