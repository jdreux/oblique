from dataclasses import dataclass, field
from typing import Literal

from core.registry import oblique_module
from processing.base_processing_operator import BaseProcessingOperator

from .base_av_module import BaseAVModule, BaseAVParams, ParamFloat, ParamInt, Uniforms


@dataclass
class VisualNoiseParams(BaseAVParams):
    """Parameters for the visual noise module."""

    noise_size: Literal["small", "medium", "large"] = field(
        default="medium",
        metadata={
            "description": "Noise grain size preset.",
            "enum_values": ["small", "medium", "large"],
        },
    )
    color_mode: Literal["gray", "rgba"] = field(
        default="gray",
        metadata={
            "description": "Output color mode for generated noise.",
            "enum_values": ["gray", "rgba"],
        },
    )
    intensity: ParamFloat = field(
        default=1.0,
        metadata={
            "min": 0.0,
            "max": 1.0,
            "description": "Overall output intensity multiplier.",
        },
    )
    speed: ParamFloat = field(
        default=1.0,
        metadata={
            "min": 0.0,
            "max": 4.0,
            "description": "Animation speed multiplier for time-based noise updates.",
        },
    )

class VisualNoiseUniforms(Uniforms, total=True):
    u_noise_scale: float
    u_intensity: float
    u_color_mode: float
    u_speed: float
    u_time: float


@oblique_module(
    category="core",
    description="Generates animated grayscale or RGBA procedural noise.",
    tags=["noisy", "evolving", "monochrome", "colorful"],
    cost_hint="low",
)
class VisualNoiseModule(BaseAVModule[VisualNoiseParams, VisualNoiseUniforms]):
    """
    Visual noise module that generates different types of noise patterns.

    Features:
    - Three noise sizes: small, medium, large
    - Two color modes: gray (monochrome) or RGBA (colorful)
    - Adjustable intensity and animation speed
    - GPU-accelerated noise generation
    """

    metadata = {
        "name": "VisualNoiseModule",
        "description": "Generates visual noise patterns with configurable size and color modes.",
        "parameters": {
            "noise_size": "small|medium|large",
            "color_mode": "gray|rgba",
            "intensity": float,
            "speed": float,
        },
    }
    frag_shader_path = "modules/core/shaders/visual-noise.frag"

    def prepare_uniforms(self, t: float) -> VisualNoiseUniforms:
        """
        Return uniforms for rendering.

        Args:
            t (float): Current time in seconds

        Returns:
            Uniforms: Uniform values to pass to the shader
        """
        # Map noise size to scale factor
        size_scale = {"small": 1, "medium": 500, "large": 10000}

        # Map color mode to shader flag
        color_mode_flag = 1.0 if self.params.color_mode == "rgba" else 0.0

        return VisualNoiseUniforms(
            u_resolution=(self._resolve_param(self.params.width), self._resolve_param(self.params.height)),
            u_time=t,
            u_noise_scale=size_scale[self.params.noise_size],
            u_intensity=self._resolve_param(self.params.intensity),
            u_color_mode=color_mode_flag,
            u_speed=self._resolve_param(self.params.speed),
        )
