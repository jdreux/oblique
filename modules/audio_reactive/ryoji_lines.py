from dataclasses import dataclass
from typing import List, Optional

from dataclasses import dataclass
from typing import List, Optional

from modules.core.base_av_module import BaseAVModule, BaseAVParams, ParamInt, ParamFloat, Uniforms
from processing.fft_bands import FFTBands
from processing.spectral_centroid import SpectralCentroid

# Hardcoded shader array size - must match the shader declaration
SHADER_BANDS_SIZE = 512


@dataclass
class RyojiLinesParams(BaseAVParams):
    """Parameters for the RyojiLines module."""

    num_bands: ParamInt = SHADER_BANDS_SIZE  # Default to full shader capacity
    fade_rate: ParamFloat = 0.95
    band_levels_processor: Optional[FFTBands] = None
    spectral_centroid_processor: Optional[SpectralCentroid] = None


class RyojiLinesUniforms(Uniforms, total=True):
    u_bands: List[float]
    u_num_bands: int
    u_spectral_brightness: float
    u_time: float


class RyojiLines(BaseAVModule[RyojiLinesParams, RyojiLinesUniforms]):
    """
    RyojiLines - Renders animated parallel lines representing FFT frequency bands.
    Each line corresponds to a frequency band and animates based on the band's amplitude.
    Lines are arranged horizontally and animate vertically with varying intensity.
    """

    metadata = {
        "name": "RyojiLines",
        "description": "Renders animated parallel lines representing FFT frequency bands with vertical animation.",
        "parameters": RyojiLinesParams.__annotations__,
    }
    frag_shader_path: str = "modules/audio_reactive/shaders/ryoji-lines.frag"

    def __init__(
        self,
        params: RyojiLinesParams,
        band_levels_processor: FFTBands,
        spectral_centroid_processor: SpectralCentroid,
    ):
        super().__init__(params)
        # Initialize with zero bands - always use shader size
        # self.bands: List[float] = [0.0] * SHADER_BANDS_SIZE
        self.band_levels_processor = band_levels_processor
        self.spectral_centroid_processor = spectral_centroid_processor

    def prepare_uniforms(self, t: float) -> RyojiLinesUniforms:
        """
        Return the uniforms needed for rendering.
        """

        bands = list(self.band_levels_processor.process())
        if len(bands) < SHADER_BANDS_SIZE:
            # Pad with zeros to reach shader size
            bands = bands + [0.0] * (SHADER_BANDS_SIZE - len(bands))
        elif len(bands) > SHADER_BANDS_SIZE:
            # Truncate to shader size
            bands = bands[:SHADER_BANDS_SIZE]
        else:
            # Exact size
            bands = bands.copy()
        spectral_brightness = self.spectral_centroid_processor.process()

        uniforms: RyojiLinesUniforms = {
            "u_time": t,
            "u_resolution": (self._resolve_param(self.params.width), self._resolve_param(self.params.height)),
            "u_bands": bands,  # Always 512 bands now
            "u_num_bands": min(
                self._resolve_param(self.params.num_bands), SHADER_BANDS_SIZE
            ),  # Use actual number of bands (up to 512)
            "u_spectral_brightness": spectral_brightness,
        }
        return uniforms
