from dataclasses import dataclass
from typing import Any

from processing.fft_bands import FFTBands

from .base_av_module import BaseAVModule, BaseAVParams


@dataclass
class IkedaTinyBarcodeParams(BaseAVParams):
    """Parameters for the Ikeda Tiny Barcode pattern module."""

    speed_scale: float = 1.0
    pattern_intensity: float = 1.0
    barcode_width: float = 32.0
    noise_scale: float = 512.0
    threshold: float = 0.1
    width: int = 800
    height: int = 600


class IkedaTinyBarcodeModule(BaseAVModule[IkedaTinyBarcodeParams]):
    """
    Ikeda Tiny Barcode module that generates a glitchy barcode pattern based on ShaderToy implementation.

    Features:
    - Glitchy barcode pattern generation
    - Texture input support (upstream texture as tex0)
    - Configurable speed and intensity
    - GPU-accelerated pattern generation
    - Based on ShaderToy implementation: https://www.shadertoy.com/view/XtdcWS
    """

    metadata = {
        "name": "IkedaTinyBarcodeModule",
        "description": "Generates a glitchy barcode pattern inspired by Ikeda's work, adapted from ShaderToy.",
        "parameters": {
            "speed_scale": float,
            "pattern_intensity": float,
            "barcode_width": float,
            "noise_scale": float,
            "threshold": float,
        },
    }
    frag_shader_path = "shaders/ikeda-tiny-barcode.frag"

    def __init__(self, params: IkedaTinyBarcodeParams, fft_bands_processor: FFTBands):
        super().__init__(params)
        self.fft_bands_processor = fft_bands_processor

    def render_data(self, t: float) -> dict[str, Any]:
        """
        Return shader path and uniforms for rendering.

        Args:
            t (float): Current time in seconds

        Returns:
            dict[str, Any]: Shader data and uniforms
        """
        uniforms = {
            "u_resolution": (self.params.width, self.params.height),
            "u_time": t * self.params.speed_scale,
            "u_pattern_intensity": self.params.pattern_intensity,
            "u_barcode_width": self.params.barcode_width,
            "u_noise_scale": self.params.noise_scale,
            "u_threshold": self.params.threshold,
        }

        # Add FFT bands
        bands = self.fft_bands_processor.process()
        uniforms["u_fft_bands"] = bands

        return {"frag_shader_path": self.frag_shader_path, "uniforms": uniforms}
