from dataclasses import dataclass, field

from core.registry import oblique_module
from modules.core.base_av_module import BaseAVModule, BaseAVParams, ParamFloat, Uniforms


@dataclass
class CalabiYauParams(BaseAVParams):
    speed: ParamFloat = field(
        default=0.6,
        metadata={"min": 0.0, "max": 3.0, "description": "Rotation speed."},
    )
    n_folds: ParamFloat = field(
        default=5.0,
        metadata={"min": 3.0, "max": 8.0, "description": "Number of CY lobes."},
    )
    scale: ParamFloat = field(
        default=0.4,
        metadata={"min": 0.1, "max": 1.0, "description": "Surface radius."},
    )
    fold_depth: ParamFloat = field(
        default=0.22,
        metadata={"min": 0.0, "max": 0.4, "description": "Depth of surface folds."},
    )
    amplitude: ParamFloat = field(
        default=0.0,
        metadata={"min": 0.0, "max": 1.0, "description": "Audio amplitude."},
    )
    bass: ParamFloat = field(
        default=0.0,
        metadata={"min": 0.0, "max": 1.0, "description": "Low-frequency energy."},
    )
    centroid: ParamFloat = field(
        default=0.0,
        metadata={"min": 0.0, "max": 1.0, "description": "Spectral centroid."},
    )


class CalabiYauUniforms(Uniforms, total=True):
    u_time: float
    u_speed: float
    u_n_folds: float
    u_scale: float
    u_fold_depth: float
    u_amplitude: float
    u_bass: float
    u_centroid: float


@oblique_module(
    category="generative",
    description="Raymarched Calabi-Yau manifold cross-section with audio-reactive folds.",
    tags=["geometric", "3d", "raymarching", "audio-reactive", "organic"],
    cost_hint="medium",
)
class CalabiYau(BaseAVModule[CalabiYauParams, CalabiYauUniforms]):
    metadata = {
        "name": "CalabiYau",
        "description": "Raymarched Calabi-Yau manifold cross-section.",
        "parameters": CalabiYauParams.__annotations__,
    }
    frag_shader_path: str = "modules/generative/shaders/calabi_yau.frag"

    def __init__(self, params: CalabiYauParams):
        super().__init__(params)

    def prepare_uniforms(self, t: float) -> CalabiYauUniforms:
        return {
            "u_resolution": (
                self._resolve_param(self.params.width),
                self._resolve_param(self.params.height),
            ),
            "u_time": t,
            "u_speed": self._resolve_param(self.params.speed),
            "u_n_folds": self._resolve_param(self.params.n_folds),
            "u_scale": self._resolve_param(self.params.scale),
            "u_fold_depth": self._resolve_param(self.params.fold_depth),
            "u_amplitude": self._resolve_param(self.params.amplitude),
            "u_bass": self._resolve_param(self.params.bass),
            "u_centroid": self._resolve_param(self.params.centroid),
        }
