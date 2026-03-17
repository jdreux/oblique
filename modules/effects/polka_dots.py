from dataclasses import dataclass, field
from typing import Tuple

from core.registry import oblique_module
from modules.core.base_av_module import BaseAVModule, BaseAVParams, ParamFloat, ParamInt, ParamTexture, Uniforms


@dataclass
class PolkaDotsParams(BaseAVParams):
    input_texture: ParamTexture = field(
        default=None,
        metadata={
            "description": "Optional input texture (for chain API compatibility).",
        },
    )
    grid_cols: ParamInt = field(
        default=12,
        metadata={
            "min": 2,
            "max": 64,
            "description": "Number of dot columns.",
        },
    )
    grid_rows: ParamInt = field(
        default=8,
        metadata={
            "min": 2,
            "max": 64,
            "description": "Number of dot rows.",
        },
    )
    dot_radius: ParamFloat = field(
        default=0.35,
        metadata={
            "min": 0.05,
            "max": 0.5,
            "description": "Dot radius relative to cell size.",
        },
    )
    hue_shift: ParamFloat = field(
        default=0.0,
        metadata={
            "min": 0.0,
            "max": 1.0,
            "description": "Rotate the entire color palette.",
        },
    )
    saturation: ParamFloat = field(
        default=1.0,
        metadata={
            "min": 0.0,
            "max": 2.0,
            "description": "Saturation multiplier for dot colors.",
        },
    )
    brightness: ParamFloat = field(
        default=1.0,
        metadata={
            "min": 0.0,
            "max": 2.0,
            "description": "Brightness multiplier for dot colors.",
        },
    )
    edge_softness: ParamFloat = field(
        default=0.02,
        metadata={
            "min": 0.0,
            "max": 0.2,
            "description": "Anti-aliasing softness at dot edges.",
        },
    )


class PolkaDotsUniforms(Uniforms, total=True):
    u_time: float
    u_resolution: Tuple[int, int]
    u_grid_cols: int
    u_grid_rows: int
    u_dot_radius: float
    u_hue_shift: float
    u_saturation: float
    u_brightness: float
    u_edge_softness: float


@oblique_module(
    category="effects",
    description="Colorful polka dots on transparent background with controllable grid and palette.",
    tags=["geometric", "pattern", "colorful", "overlay"],
    cost_hint="low",
)
class PolkaDotsModule(BaseAVModule[PolkaDotsParams, PolkaDotsUniforms]):

    metadata = {
        "name": "PolkaDotsModule",
        "description": "Colorful polka dots on transparent background.",
        "parameters": PolkaDotsParams.__annotations__,
    }
    frag_shader_path: str = "modules/effects/shaders/polka-dots.frag"

    def __init__(self, params: PolkaDotsParams):
        super().__init__(params)

    def prepare_uniforms(self, t: float) -> PolkaDotsUniforms:
        uniforms: PolkaDotsUniforms = {
            "u_time": t,
            "u_resolution": self._resolve_resolution(),
            "u_grid_cols": self._resolve_param(self.params.grid_cols),
            "u_grid_rows": self._resolve_param(self.params.grid_rows),
            "u_dot_radius": self._resolve_param(self.params.dot_radius),
            "u_hue_shift": self._resolve_param(self.params.hue_shift),
            "u_saturation": self._resolve_param(self.params.saturation),
            "u_brightness": self._resolve_param(self.params.brightness),
            "u_edge_softness": self._resolve_param(self.params.edge_softness),
        }
        return uniforms
