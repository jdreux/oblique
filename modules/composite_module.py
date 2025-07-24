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
    PASSTHROUGH_LEFT = 24
    PASSTHROUGH_RIGHT = 25

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
    u_resolution: Tuple[int, int]
    tex0: moderngl.Texture
    tex1: moderngl.Texture
    u_op: int

class CompositeModule(BaseAVModule[CompositeParams]):
    """
    Composite module that blends two input modules using a selectable blend/composite operation.
    Supported operations: add, average, multiply, screen, overlay, difference, subtract, hardlight, colorburn, colordodge, hue, color, reflect, glow, pinlight, exclusion, negation, linearburn, lineardodge, linearlight, vividlight, hardmix, darken, lighten.
    """
    metadata = {
        "name": "CompositeModule",
        "description": "Blends two input modules using a selectable blend/composite operation.",
        "parameters": CompositeParams.__annotations__,
    }
    frag_shader_path: str = "shaders/composite.frag"

    def __init__(self, params: CompositeParams, module0: BaseAVModule, module1: BaseAVModule):
        super().__init__(params)
        self.module0 = module0
        self.module1 = module1
        self.width = self.params.width
        self.height = self.params.height

    def render_data(self, t: float) -> RenderData:
        uniforms: CompositeUniforms = {
            "u_resolution": (self.width, self.height),
            "tex0": self.tex0,
            "tex1": self.tex1,
            "u_op": self.params.operation.value,
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
        self.tex0 = self.module0.render_texture(ctx, width, height, t)
        self.tex1 = self.module1.render_texture(ctx, width, height, t)
        return super().render_texture(ctx, width, height, t)

if __name__ == "__main__":
    # Example test runner for CompositeModule

    import moderngl
    import numpy as np

    from modules.pauric_squares_module import PauricSquaresModule, PauricSquaresParams
    from modules.visual_noise import VisualNoiseModule, VisualNoiseParams

    width, height = 800, 600
    ctx = moderngl.create_standalone_context()
    noise = VisualNoiseModule(VisualNoiseParams(width=width, height=height))
    squares = PauricSquaresModule(PauricSquaresParams(width=width, height=height))
    composite = CompositeModule(CompositeParams(width=width, height=height, operation=CompositeOp.ADD), noise, squares)
    tex = composite.render_texture(ctx, width, height, t=0.0)
    img = np.frombuffer(tex.read(), dtype=np.uint8).reshape((height, width, 4))
    print("CompositeModule test image shape:", img.shape)
