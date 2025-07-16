from dataclasses import dataclass
from typing import Any, Optional

import moderngl

from core.renderer import render_to_texture
from modules.base_av_module import BaseAVModule, BaseAVParams, Uniforms


@dataclass
class FeedbackParams(BaseAVParams):
    """Parameters for the Feedback module."""

    feedback_strength: float = 1.0  # How much previous frame to blend (0.0=no feedback, 1.0=infinite feedback)
    reset_on_start: bool = True      # Clear buffer on module start
    blend_mode: str = "additive"     # Currently only additive supported


class FeedbackUniforms(Uniforms, total=True):
    u_time: float
    u_resolution: tuple[int, int]
    u_feedback_strength: float
    u_feedback_texture: moderngl.Texture | None
    u_input_texture: moderngl.Texture | None


class Feedback(BaseAVModule[FeedbackParams]):
    """
    Feedback module that provides access to the previous frame's output.
    Enables feedback loops for effects like trails, motion blur, and recursive patterns.

    The module stores the previous frame and provides it as a texture uniform
    to shaders, allowing them to blend current output with previous frames.
    """

    metadata = {
        "name": "Feedback",
        "description": "Provides previous frame texture for feedback effects like trails and motion blur.",
        "parameters": FeedbackParams.__annotations__,
    }
    frag_shader_path: str = "shaders/feedback.frag"

    def __init__(self, params: FeedbackParams, upstream_module: "BaseAVModule"):
        super().__init__(params)
        self.width = self.params.width
        self.height = self.params.height

        # Feedback texture storage
        self.previous_frame: Optional[moderngl.Texture] = None
        self.feedback_initialized = False

        # Upstream module for input
        self.upstream_module = upstream_module

        # Initialize feedback texture if reset_on_start is True
        if self.params.reset_on_start:
            self.reset_feedback()

    def reset_feedback(self) -> None:
        """Reset the feedback buffer by clearing the previous frame."""

        self.previous_frame = None
        self.feedback_initialized = False

    def set_feedback_strength(self, strength: float) -> None:
        """
        Set the feedback strength parameter.

        Args:
            strength: Feedback strength from 0.0 to 1.0
        """
        self.params.feedback_strength = max(0.0, min(1.0, strength))

    def render_data(self, t: float) -> dict[str, Any]:
        """
        Return the data needed for the renderer to render this module.
        """

        uniforms: FeedbackUniforms = {
            "u_time": t,
            "u_resolution": (self.width, self.height),
            "u_feedback_strength": self.params.feedback_strength,
            "u_feedback_texture": self.previous_frame if self.previous_frame else None,
            "u_input_texture": None,  # Will be set in render_texture
        }

        return {
            "frag_shader_path": self.frag_shader_path,
            "uniforms": uniforms,
        }

    # TODO: this must be really leaky from memory POV - review.
    def render_texture(
        self,
        ctx: moderngl.Context,
        width: int,
        height: int,
        t: float,
        filter=moderngl.NEAREST,
    ) -> moderngl.Texture:
        """
        Override render_texture to handle feedback texture management.
        Stores the current frame as the previous frame for the next render.
        """
        # Initialize feedback texture if needed
        if self.previous_frame is None:
            self.previous_frame = ctx.texture(
                (width, height), 4, dtype="f1", alignment=1
            )
            self.previous_frame.filter = (filter, filter)
            self.previous_frame.repeat_x = False
            self.previous_frame.repeat_y = False
            self.feedback_initialized = True

        # Get input texture from upstream module if available
        input_texture = None
        if self.upstream_module:
            input_texture = self.upstream_module.render_texture(ctx, width, height, t)

        # Update uniforms with input texture
        uniforms = self.render_data(t)["uniforms"]
        uniforms["u_input_texture"] = input_texture

        # Render the current frame
        current_frame = render_to_texture(
            ctx,
            width,
            height,
            self.frag_shader_path,
            uniforms,
            filter,
        )

        # Store current frame as previous frame for next render
        # Copy the current frame to the previous frame texture
        # TODO: note for later: this is this really needed? why can't we just use current_frame, it has alraedy been rendered.
        if self.feedback_initialized:
            # Create a framebuffer to copy the texture
            fbo = ctx.framebuffer(color_attachments=[self.previous_frame])
            fbo.use()
            ctx.viewport = (0, 0, width, height)

            # Render the current frame to the previous frame texture
            from core.renderer import render_fullscreen_quad

            render_fullscreen_quad(
                ctx, "shaders/passthrough.frag", {"u_texture": current_frame}
            )

        return current_frame
