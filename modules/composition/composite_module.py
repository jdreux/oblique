from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple

import moderngl

from modules.core.base_av_module import BaseAVModule, BaseAVParams, ParamFloat, ParamTexture, Uniforms


class CompositeOp(int, Enum):
    ADD = 0
    AVERAGE = 1
    MULTIPLY = 2
    SCREEN = 3
    OVERLAY = 4
    DIFFERENCE = 5
    SUBTRACT = 6
    HARDLIGHT = 7
    COLORBURN = 8
    COLORDODGE = 9
    HUE = 10
    COLOR = 11
    REFLECT = 12
    GLOW = 13
    PINLIGHT = 14
    EXCLUSION = 15
    NEGATION = 16
    LINEARBURN = 17
    LINEARDODGE = 18
    LINEARLIGHT = 19
    VIVIDLIGHT = 20
    HARDMIX = 21
    DARKEN = 22
    LIGHTEN = 23
    PASSTHROUGH_TOP = 24
    PASSTHROUGH_BOTTOM = 25
    ATOP = 26

@dataclass
class CompositeParams(BaseAVParams):
    """
    Parameters for the Composite module.
    Attributes:
        width (int): Output width
        height (int): Output height
        operation (CompositeOp): Blend/composite operation to use
    """
    top_texture: ParamTexture
    bottom_texture: ParamTexture
    operation: CompositeOp = CompositeOp.ADD
    mix: ParamFloat = field(
        default=1.0,
        metadata={
            "min": 0.0,
            "max": 1.0,
            "description": "Blend amount. 0.0=bottom only, 1.0=full blend",
        },
    )

class CompositeUniforms(Uniforms, total=True):
    top_tex: moderngl.Texture
    bottom_tex: moderngl.Texture
    u_op: int
    u_mix: float

class CompositeModule(BaseAVModule[CompositeParams, CompositeUniforms]):
    """
    Composite module that blends two input modules using a selectable blend/composite operation.
    Supported operations: see CompositeOp enum.
    """
    metadata = {
        "name": "CompositeModule",
        "description": "Blends two input modules using a selectable blend/composite operation.",
        "parameters": CompositeParams.__annotations__,
    }
    frag_shader_path: str = "modules/composition/shaders/composite.frag"

    def __init__(self, params: CompositeParams):
        super().__init__(params)

    def prepare_uniforms(self, t: float) -> CompositeUniforms:
        uniforms: CompositeUniforms = {
            "u_resolution": (self._resolve_param(self.params.width), self._resolve_param(self.params.height)),
            "top_tex": self.params.top_texture,
            "bottom_tex": self.params.bottom_texture,
            "u_op": int(self.params.operation),
            "u_mix": self._resolve_param(self.params.mix),
        }
        return uniforms
