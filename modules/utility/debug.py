from dataclasses import dataclass, field

from core.registry import oblique_module
from modules.core.base_av_module import BaseAVModule, BaseAVParams, ParamInt, ParamFloat, Uniforms


@dataclass
class DebugParams(BaseAVParams):
    number: ParamFloat = field(
        default=0.0,
        metadata={
            "min": -1000000.0,
            "max": 1000000.0,
            "description": "Numeric value exposed to the debug shader for inspection.",
        },
    )
    width: ParamInt = 800
    height: ParamInt = 600

class DebugUniforms(Uniforms, total=True):
    u_number: float


@oblique_module(
    category="utility",
    description="Displays numeric debug values with minimal shader output.",
    tags=["minimal", "clean", "static"],
    cost_hint="low",
)
class DebugModule(BaseAVModule[DebugParams, DebugUniforms]):
    """
    Debug module that displays an input number and string using a shader.
    """

    metadata = {
        "name": "DebugModule",
        "description": "Displays an input number and string for debugging purposes.",
        "parameters": {"number": float, "text": str},
    }
    frag_shader_path = "modules/utility/shaders/debug.frag"

    def prepare_uniforms(self, t: float) -> DebugUniforms:
        return DebugUniforms(
            u_number=self._resolve_param(self.params.number),
            u_resolution=self._resolve_resolution()
        )
