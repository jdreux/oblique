"""
Temporary Oblique Patch - Basic Template
Edit this file and reload using reload_patch() or r() in the REPL
"""

from math import cos, sin

from core.oblique_patch import ObliquePatch
from modules.core.base_av_module import BaseAVModule
from modules.core.visual_noise import VisualNoiseModule, VisualNoiseParams
from modules.effects.feedback import FeedbackModule, FeedbackParams


def temp_patch(width: int, height: int) -> ObliquePatch:
    """
    Basic patch template with simple visual noise.
    
    Args:
        width: Window width
        height: Window height
        
    Returns:
        Configured ObliquePatch instance
    """

    # Create a simple visual noise module
    noise_module = VisualNoiseModule(
        VisualNoiseParams(
            width=width,
            height=height,
            noise_size="large",
            color_mode="rgba",
            intensity=1.0,
            speed=1.0,
        )
    )

    feedback_module = FeedbackModule(
        FeedbackParams(
            width=width,
            height=height,
            input_texture=noise_module,
            feedback_strength=0.5,
            direction=(0,0)
        )
    )

    def tick_callback(t: float) -> BaseAVModule:
        # Animate noise scale over time
        noise_module.params.speed = sin(t * 0.3) * 0.01
        noise_module.params.intensity = 1.0 + 0.5 * cos(t * 0.5)
        feedback_module.params.direction = (sin(t * 0.3), cos(t * 0.3))

        return feedback_module

    return ObliquePatch(
        tick_callback=tick_callback,
    )
