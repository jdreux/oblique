"""
Temporary Oblique Patch - Basic Template
Edit this file and reload using reload_patch() or r() in the REPL
"""

from math import cos, sin

from core.oblique_patch import ObliquePatch
from modules.audio_reactive.blue_back_n_gray import BlueBackNGrayModule, BlueBackNGrayParams
from modules.core.base_av_module import BaseAVModule
from modules.effects.feedback import FeedbackModule, FeedbackParams
from inputs.midi.core.midi_input import list_midi_input_ports, print_midi_input_ports
from inputs.audio.core.audio_device_input import list_audio_devices, print_audio_devices


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
    blue_back_n_gray_module = BlueBackNGrayModule(
        BlueBackNGrayParams(
            width=width,
            height=height,
            strip_offset=50.0,
            n_circles=64,
        )
    )


    feedback_module = FeedbackModule(
        FeedbackParams(
            width=width,
            height=height,
            input_texture=blue_back_n_gray_module   ,
            feedback_strength=0.5,
            direction=(0,0)
        )
    )

    def tick_callback(t: float) -> BaseAVModule:
        blue_back_n_gray_module.params.strip_offset = 50.0 * (sin(t*0.1) - 0.5)
        feedback_module.params.direction = (sin(t * 0.3), cos(t * 0.3))

        return feedback_module

    return ObliquePatch(
        tick_callback=tick_callback,
    )
