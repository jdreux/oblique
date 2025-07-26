from dataclasses import dataclass
from enum import Enum
from typing import Tuple

import moderngl

from modules.base_av_module import BaseAVModule, BaseAVParams, RenderData, Uniforms


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
    operation: CompositeOp = CompositeOp.ADD
    width: int = 800
    height: int = 600

class CompositeUniforms(Uniforms, total=True):
    top_tex: moderngl.Texture
    bottom_tex: moderngl.Texture
    u_op: int

class CompositeModule(BaseAVModule[CompositeParams]):
    """
    Composite module that blends two input modules using a selectable blend/composite operation.
    Supported operations: see CompositeOp enum.
    """
    metadata = {
        "name": "CompositeModule",
        "description": "Blends two input modules using a selectable blend/composite operation.",
        "parameters": CompositeParams.__annotations__,
    }
    frag_shader_path: str = "shaders/composite.frag"

    def __init__(self, params: CompositeParams, top_module: BaseAVModule, bottom_module: BaseAVModule):
        super().__init__(params)
        self.top_module = top_module
        self.bottom_module = bottom_module
        self.width = self.params.width
        self.height = self.params.height

    def prepare_uniforms(self, t: float) -> RenderData:
        uniforms: CompositeUniforms = {
            "u_resolution": (self.width, self.height),
            "top_tex": self.top_tex,
            "bottom_tex": self.bottom_tex,
            "u_op": int(self.params.operation),
        }
        return RenderData(
            frag_shader_path=self.frag_shader_path,
            uniforms=uniforms,
        )

    def render_texture(
        self,
        ctx: moderngl.Context,
        width: int,
        height: int,
        t: float,
        filter=moderngl.NEAREST,
    ) -> moderngl.Texture:
        self.top_tex = self.top_module.render_texture(ctx, width, height, t)
        self.bottom_tex = self.bottom_module.render_texture(ctx, width, height, t)
        return super().render_texture(ctx, width, height, t)