from dataclasses import dataclass
from typing import Optional

import moderngl

from modules.base_av_module import BaseAVModule, BaseAVParams, ParamFloat, ParamTexture, RenderData, Uniforms


@dataclass
class FeedbackParams(BaseAVParams):
    """Parameters for the Feedback module."""
    
    input_texture: ParamTexture  # Input texture for feedback
    feedback_strength: ParamFloat = 0.97  # How much previous frame to blend. Decay rate per second is
    # feedback_strength^frame_rate so it decays very quickly.
    direction: tuple[ParamFloat, ParamFloat] = (0, 0)  # direction of the feedback effect -- 0,0 is in place


class FeedbackUniforms(Uniforms, total=True):
    u_time: float
    u_resolution: tuple[int, int]
    u_feedback_strength: float
    u_feedback_texture: moderngl.Texture | None
    u_input_texture: moderngl.Texture | None
    u_direction: tuple[float, float]


class FeedbackModule(BaseAVModule[FeedbackParams]):
    """
    Feedback module that provides access to the previous frame's output.
    Enables feedback loops for effects like trails, motion blur, and recursive patterns.

    The module stores the previous frame and provides it as a texture uniform
    to shaders, allowing them to blend current output with previous frames.
    """

    metadata = {
        "name": "FeedbackModule",
        "description": "Provides previous frame texture for feedback effects like trails and motion blur.",
        "parameters": FeedbackParams.__annotations__,
    }
    frag_shader_path: str = "shaders/feedback.frag"

    def __init__(self, params: FeedbackParams):
        super().__init__(params)
        self.width = self.params.width
        self.height = self.params.height

        # Feedback texture storage
        self.previous_frame: Optional[moderngl.Texture] = None
        self.input_tex: Optional[moderngl.Texture] = None

        # Cached framebuffer for texture copying
        self._cached_fbo: Optional[moderngl.Framebuffer] = None

    def reset_feedback(self) -> None:
        """Reset the feedback buffer by clearing the previous frame."""

        self.previous_frame = None
        self.feedback_initialized = False

    def cleanup(self) -> None:
        """Clean up resources when the module is destroyed."""
        if self._cached_fbo is not None:
            self._cached_fbo.release()
            self._cached_fbo = None

        if self.previous_frame is not None:
            self.previous_frame.release()
            self.previous_frame = None

    def prepare_uniforms(self, t: float) -> RenderData:
        """
        Return the data needed for the renderer to render this module.
        """
        uniforms: FeedbackUniforms = {
            "u_time": t,
            "u_resolution": self._resolve_resolution(),
            "u_feedback_strength": self._resolve_param(self.params.feedback_strength),
            "u_feedback_texture": self.previous_frame if self.previous_frame else None,
            "u_input_texture": self.input_tex if self.input_tex else None,
            "u_direction": (
                self._resolve_param(self.params.direction[0]),
                self._resolve_param(self.params.direction[1]),
            ),
        }

        return RenderData(
            frag_shader_path=self.frag_shader_path,
            uniforms=uniforms,
        )

    def copy_texture_to_previous_frame(
        self, ctx: moderngl.Context, width: int, height: int, texture: moderngl.Texture
    ) -> None:
        """
        Copy the texture from the input module to the previous frame.
        """
        # Initialize feedback texture if needed
        if self.previous_frame is None:
            self.previous_frame = ctx.texture((width, height), 4, dtype="f1", alignment=1)
            self.previous_frame.filter = (moderngl.NEAREST, moderngl.NEAREST)
            self.previous_frame.repeat_x = False
            self.previous_frame.repeat_y = False

        # Create or reuse cached framebuffer
        if self._cached_fbo is None:
            self._cached_fbo = ctx.framebuffer(color_attachments=[self.previous_frame])

        try:
            self._cached_fbo.use()
            ctx.viewport = (0, 0, width, height)

            # Render the current frame to the previous frame texture
            from core.renderer import render_fullscreen_quad

            render_fullscreen_quad(ctx, "shaders/passthrough.frag", {"u_texture": texture})
        finally:
            ctx.screen.use()

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

        # Get input texture from input module
        self.input_tex = self._resolve_texture_param(self.params.input_texture, ctx, width, height, t, filter)

        if self.previous_frame is None:
            self.copy_texture_to_previous_frame(ctx, width, height, self.input_tex)

        # Render the module to a texture
        current_frame = super().render_texture(ctx, width, height, t)

        # Copy current frame to previous frame texture for next render
        self.copy_texture_to_previous_frame(ctx, width, height, current_frame)

        return current_frame
