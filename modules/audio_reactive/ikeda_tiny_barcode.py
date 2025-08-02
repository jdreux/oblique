from dataclasses import dataclass

from processing.fft_bands import FFTBands

from modules.core.base_av_module import BaseAVModule, BaseAVParams, ParamFloat, ParamFloatList, ParamInt, Uniforms


@dataclass
class IkedaTinyBarcodeParams(BaseAVParams):
    """Parameters for the Ikeda Tiny Barcode pattern module."""
    fft_bands: ParamFloatList
    speed_scale: ParamFloat = 1.0
    pattern_intensity: ParamFloat = 1.0
    barcode_width: ParamFloat = 32.0
    noise_scale: ParamFloat = 512.0
    threshold: ParamFloat = 0.1



class IkedaTinyBarcodeUniforms(Uniforms, total=True):
    u_resolution: tuple[int, int]
    u_time: float
    u_pattern_intensity: float
    u_barcode_width: float
    u_noise_scale: float
    u_threshold: float
    u_fft_bands: list[float]


class IkedaTinyBarcodeModule(BaseAVModule[IkedaTinyBarcodeParams, IkedaTinyBarcodeUniforms]):
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
            "fft_bands": list[float],
        },
    }
    frag_shader_path = "modules/audio_reactive/shaders/ikeda-tiny-barcode.frag"

    def __init__(self, params: IkedaTinyBarcodeParams):
        super().__init__(params)

    def prepare_uniforms(self, t: float) -> IkedaTinyBarcodeUniforms:
        """
        Return uniforms for rendering.

        Args:
            t (float): Current time in seconds

        Returns:
            Uniforms: Uniform values to pass to the shader
        """
        uniforms: IkedaTinyBarcodeUniforms = {
            "u_resolution": (self._resolve_param(self.params.width), self._resolve_param(self.params.height)),
            "u_time": t * self._resolve_param(self.params.speed_scale),
            "u_pattern_intensity": self._resolve_param(self.params.pattern_intensity),
            "u_barcode_width": self._resolve_param(self.params.barcode_width),
            "u_noise_scale": self._resolve_param(self.params.noise_scale),
            "u_threshold": self._resolve_param(self.params.threshold),
            "u_fft_bands": self._resolve_param(self.params.fft_bands),
        }

        return uniforms
