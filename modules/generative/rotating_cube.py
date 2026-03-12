from dataclasses import dataclass, field

from core.registry import oblique_module
from modules.core.base_av_module import BaseAVModule, BaseAVParams, ParamFloat, Uniforms


@dataclass
class RotatingCubeParams(BaseAVParams):
    speed: ParamFloat = field(
        default=1.0,
        metadata={
            "min": 0.0,
            "max": 5.0,
            "description": "Rotation speed multiplier.",
        },
    )
    edge_width: ParamFloat = field(
        default=2.0,
        metadata={
            "min": 0.5,
            "max": 8.0,
            "description": "Width of cube edges in pixels.",
        },
    )
    cube_size: ParamFloat = field(
        default=0.2,
        metadata={
            "min": 0.1,
            "max": 0.8,
            "description": "Size of the cube relative to the viewport.",
        },
    )
    amplitude: ParamFloat = field(
        default=0.0,
        metadata={
            "min": 0.0,
            "max": 1.0,
            "description": "Overall audio amplitude (RMS).",
        },
    )
    bass: ParamFloat = field(
        default=0.0,
        metadata={
            "min": 0.0,
            "max": 1.0,
            "description": "Low-frequency energy for bass-driven effects.",
        },
    )
    centroid: ParamFloat = field(
        default=0.0,
        metadata={
            "min": 0.0,
            "max": 1.0,
            "description": "Spectral centroid for color temperature.",
        },
    )
    explode: ParamFloat = field(
        default=0.0,
        metadata={
            "min": 0.0,
            "max": 1.0,
            "description": "Vertex displacement strength on transients.",
        },
    )


class RotatingCubeUniforms(Uniforms, total=True):
    u_time: float
    u_speed: float
    u_edge_width: float
    u_cube_size: float
    u_amplitude: float
    u_bass: float
    u_centroid: float
    u_explode: float


@oblique_module(
    category="generative",
    description="Wireframe rotating cube with audio-reactive size, glow, and color.",
    tags=["geometric", "wireframe", "3d", "audio-reactive", "minimal"],
    cost_hint="low",
)
class RotatingCube(BaseAVModule[RotatingCubeParams, RotatingCubeUniforms]):
    metadata = {
        "name": "RotatingCube",
        "description": "Wireframe rotating cube with audio-reactive modulation.",
        "parameters": RotatingCubeParams.__annotations__,
    }
    frag_shader_path: str = "modules/generative/shaders/rotating_cube.frag"

    def __init__(self, params: RotatingCubeParams):
        super().__init__(params)

    def prepare_uniforms(self, t: float) -> RotatingCubeUniforms:
        return {
            "u_resolution": (
                self._resolve_param(self.params.width),
                self._resolve_param(self.params.height),
            ),
            "u_time": t,
            "u_speed": self._resolve_param(self.params.speed),
            "u_edge_width": self._resolve_param(self.params.edge_width),
            "u_cube_size": self._resolve_param(self.params.cube_size),
            "u_amplitude": self._resolve_param(self.params.amplitude),
            "u_bass": self._resolve_param(self.params.bass),
            "u_centroid": self._resolve_param(self.params.centroid),
            "u_explode": self._resolve_param(self.params.explode),
        }
