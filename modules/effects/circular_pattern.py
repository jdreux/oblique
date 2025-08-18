from dataclasses import dataclass

from modules.core.base_av_module import (
    BaseAVModule,
    BaseAVParams,
    ParamFloat,
    ParamInt,
    Uniforms,
)


@dataclass
class CircularPatternParams(BaseAVParams):
    """Parameters for the CircularPattern module."""

    ring_count: ParamFloat = 80.0  # Number of concentric rings
    segment_count: ParamInt = 64  # Angular segmentation
    line_width: ParamFloat = 0.02  # Thickness of the ring lines
    noise_amplitude: ParamFloat = 0.3  # Amount of radial distortion
    speed: ParamFloat = 0.25  # Animation speed for noise


class CircularPatternUniforms(Uniforms, total=True):
    u_time: float
    u_ring_count: float
    u_segment_count: int
    u_line_width: float
    u_noise_amplitude: float
    u_speed: float


class CircularPatternModule(BaseAVModule[CircularPatternParams, CircularPatternUniforms]):
    """Generate concentric circular lines with angular noise displacement."""

    metadata = {
        "name": "CircularPatternModule",
        "description": (
            "Generates concentric circular lines distorted per-segment with"
            " simplex noise."
        ),
        "parameters": CircularPatternParams.__annotations__,
    }
    frag_shader_path: str = "modules/effects/shaders/circular-pattern.frag"

    def __init__(self, params: CircularPatternParams):
        super().__init__(params)

    def prepare_uniforms(self, t: float) -> CircularPatternUniforms:
        uniforms: CircularPatternUniforms = {
            "u_time": t,
            "u_resolution": self._resolve_resolution(),
            "u_ring_count": self._resolve_param(self.params.ring_count),
            "u_segment_count": self._resolve_param(self.params.segment_count),
            "u_line_width": self._resolve_param(self.params.line_width),
            "u_noise_amplitude": self._resolve_param(self.params.noise_amplitude),
            "u_speed": self._resolve_param(self.params.speed),
        }

        return uniforms
