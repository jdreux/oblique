from math import sin

from core.oblique_patch import ObliquePatch
from modules.audio_reactive.blue_back_n_gray import BlueBackNGrayModule, BlueBackNGrayParams
from modules.audio_reactive.ikeda_test_pattern import IkedaTestPatternModule, IkedaTestPatternParams
from modules.audio_reactive.mit_particles import MITParticlesModule, MITParticlesParams
from modules.audio_reactive.protoplasm import ProtoplasmModule, ProtoplasmParams
from modules.core.base_av_module import BaseAVModule
from modules.effects.barrel_distortion import BarrelDistortionModule
from modules.effects.blur_module import BlurModule
from modules.effects.feedback import FeedbackModule
from modules.utility.debug import DebugModule, DebugParams


def oblique_patch(width: int, height: int) -> ObliquePatch:

    debug_module = DebugModule(
        DebugParams(width=width, height=height)
    )

    ikeda_test_pattern_module = IkedaTestPatternModule(
        IkedaTestPatternParams(width=width, height=height)
    )

    protoplasm_module = ProtoplasmModule(
        ProtoplasmParams(width=width, height=height)
    )

    # --- Effect chains using .to() ---

    blur_module = (
        ikeda_test_pattern_module
        .to(BarrelDistortionModule)
        .to(BlurModule, blur_amount=1000000.0, kernel_size=5)
    )

    feedback_module = protoplasm_module.to(
        FeedbackModule, direction=(0.0, 0.0), feedback_strength=0.9
    )

    mit_particles_module = MITParticlesModule(
        MITParticlesParams(width=width, height=height)
    )

    blue_back_n_gray_module = BlueBackNGrayModule(
        BlueBackNGrayParams(
            width=width,
            height=height,
            strip_offset=50.0,
            n_circles=64,
        )
    )

    def tick_callback(t: float) -> BaseAVModule:
        blue_back_n_gray_module.params.strip_offset = 50.0 * (sin(t) - 0.5)
        return blue_back_n_gray_module

    return ObliquePatch(tick_callback=tick_callback)
