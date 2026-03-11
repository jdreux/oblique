from dataclasses import dataclass, field

import moderngl

from core.registry import oblique_module
from modules.core.base_av_module import BaseAVModule, BaseAVParams, ParamFloat, ParamTexture, Uniforms


@dataclass
class FeedbackParams(BaseAVParams):
    """Parameters for the Feedback module."""

    input_texture: ParamTexture = field(
        metadata={
            "description": "Current frame texture blended with the feedback buffer.",
        }
    )
    feedback_strength: ParamFloat = field(
        default=0.97,
        metadata={
            "min": 0.0,
            "max": 1.0,
            "description": "Per-frame blend amount from the previous frame.",
        },
    )
    direction: tuple[ParamFloat, ParamFloat] = field(
        default=(0.0, 0.0),
        metadata={
            "min": -1.0,
            "max": 1.0,
            "description": "UV offset applied when sampling the previous feedback frame.",
        },
    )


class FeedbackUniforms(Uniforms, total=True):
    u_time: float
    u_resolution: tuple[int, int]
    u_feedback_strength: float
    u_input_texture: moderngl.Texture
    u_direction: tuple[float, float]


@oblique_module(
    category="effects",
    description="Blends current and previous frames to create feedback trails.",
    tags=["feedback", "distortion", "evolving"],
    cost_hint="low",
)
class FeedbackModule(BaseAVModule[FeedbackParams, FeedbackUniforms]):
    """
    Feedback module that provides access to the previous frame's output via a ping-pong texture pass.
    Enables feedback loops for effects like trails, motion blur, and recursive patterns.
    """

    metadata = {
        "name": "FeedbackModule",
        "description": "Provides previous frame texture for feedback effects like trails and motion blur.",
        "parameters": FeedbackParams.__annotations__,
    }
    frag_shader_path: str = "modules/effects/shaders/feedback.frag"
    ping_pong: bool = True
    previous_uniform_name: str = "u_feedback_texture"

    def __init__(self, params: FeedbackParams):
        super().__init__(params)

    def prepare_uniforms(self, t: float) -> FeedbackUniforms:
        """
        Return the uniforms needed for rendering.
        """
        uniforms: FeedbackUniforms = {
            "u_time": t,
            "u_resolution": self._resolve_resolution(),
            "u_feedback_strength": self._resolve_param(self.params.feedback_strength),
            "u_input_texture": self.params.input_texture,
            "u_direction": (
                self._resolve_param(self.params.direction[0]),
                self._resolve_param(self.params.direction[1]),
            ),
        }

        return uniforms
