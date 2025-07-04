from dataclasses import dataclass
from typing import Any, List, Tuple
from typing import TypedDict
from modules.base_av_module import BaseAVModule, Uniforms, BaseAVParams
from processing.fft_bands import FFTBands
from typing import Optional
from processing.spectral_centroid import SpectralCentroid

# Hardcoded shader array size - must match the shader declaration
SHADER_BANDS_SIZE = 512

@dataclass
class RyojiLinesParams(BaseAVParams):
    """Parameters for the RyojiLines module."""
    num_bands: int = SHADER_BANDS_SIZE  # Default to full shader capacity
    fade_rate: float = 0.95
    band_levels_processor: Optional[FFTBands] = None
    spectral_centroid_processor: Optional[SpectralCentroid] = None

class RyojiLinesUniforms(Uniforms, total=True):
    u_time: float
    u_resolution: Tuple[int, int]
    u_bands: List[float]
    u_num_bands: int
    u_spectral_brightness: float
    # u_fade_rate: float

class RyojiLines(BaseAVModule[RyojiLinesParams]):
    """
    RyojiLines - Renders animated parallel lines representing FFT frequency bands.
    Each line corresponds to a frequency band and animates based on the band's amplitude.
    Lines are arranged horizontally and animate vertically with varying intensity.
    """
    metadata = {
        'name': 'RyojiLines',
        'description': 'Renders animated parallel lines representing FFT frequency bands with vertical animation.',
        'parameters': RyojiLinesParams.__annotations__,
    }
    frag_shader_path: str = 'shaders/ryoji-lines.frag'

    def __init__(self, params: RyojiLinesParams = RyojiLinesParams(), band_levels_processor: Optional[FFTBands] = None, spectral_centroid_processor: Optional[SpectralCentroid] = None):
        super().__init__(params)
        self.width = self.params.width
        self.height = self.params.height
        # Initialize with zero bands - always use shader size
        self.bands: List[float] = [0.0] * SHADER_BANDS_SIZE
        self.band_levels_processor = band_levels_processor
        self.spectral_centroid_processor = spectral_centroid_processor
        self.spectral_brightness = 0.5
        

    def set_bands(self, bands: List[float]) -> None:
        """
        Set the FFT band amplitudes.
        
        Args:
            bands: List of band amplitudes (will be padded to 512 with zeros)
        """
        # Always ensure we have exactly SHADER_BANDS_SIZE bands
        if len(bands) < SHADER_BANDS_SIZE:
            # Pad with zeros to reach shader size
            self.bands = bands + [0.0] * (SHADER_BANDS_SIZE - len(bands))
        elif len(bands) > SHADER_BANDS_SIZE:
            # Truncate to shader size
            self.bands = bands[:SHADER_BANDS_SIZE]
        else:
            # Exact size
            self.bands = bands.copy()

    def render(self, t: float) -> dict[str, Any]:
        """
        Return the data needed for the renderer to render this module.
        """
        if self.band_levels_processor is not None:
            # Get bands from processor and ensure proper size
            processor_bands = self.band_levels_processor.process()
            self.set_bands(processor_bands)
        
        if self.spectral_centroid_processor is not None:
            self.spectral_brightness = self.spectral_centroid_processor.process()

        uniforms: RyojiLinesUniforms = {
            'u_time': t,
            'u_resolution': (self.width, self.height),
            'u_bands': self.bands,  # Always 512 bands now
            'u_num_bands': min(self.params.num_bands, SHADER_BANDS_SIZE),  # Use actual number of bands (up to 512)
            'u_spectral_brightness': self.spectral_brightness,
            # 'u_line_thickness': self.params.line_thickness,
            # 'u_line_spacing': self.params.line_spacing,
            # 'u_animation_speed': self.params.animation_speed,
            # 'u_color_intensity': self.params.color_intensity,
            # 'u_fade_rate': self.params.fade_rate,
        }
        return {
            'frag_shader_path': self.frag_shader_path,
            'uniforms': uniforms,
        }

if __name__ == "__main__":
    # Test the module
    params = RyojiLinesParams(
        width=800, 
        height=600,
        num_bands=8,  # Test with fewer bands than shader size
    )
    ryoji_lines = RyojiLines(params)
    
    # Simulate some FFT bands (fewer than 512)
    test_bands = [0.1, 0.3, 0.7, 0.9, 0.5, 0.2, 0.8, 0.4]
    ryoji_lines.set_bands(test_bands)
    
    # Test render
    result = ryoji_lines.render(1.5)
    print(f"Render result: {result}")
    print(f"Number of bands sent to shader: {len(result['uniforms']['u_bands'])}")
    print(f"u_num_bands value: {result['uniforms']['u_num_bands']}") 
    print(f"Render result: {result}") 