from math import sin
from core.logger import error, info
from core.oblique_engine import ObliqueEngine
from core.oblique_patch import ObliquePatch
from modules.audio_reactive.mit_particles import MITParticlesModule, MITParticlesParams
from modules.effects.barrel_distortion import BarrelDistortionModule, BarrelDistortionParams
from modules.core.base_av_module import BaseAVModule
from modules.effects.blur_module import BlurModule, BlurParams
from modules.utility.debug import DebugModule, DebugParams
from modules.effects.feedback import FeedbackModule, FeedbackParams
from modules.audio_reactive.ikeda_test_pattern import IkedaTestPatternModule, IkedaTestPatternParams
from modules.audio_reactive.protoplasm import ProtoplasmModule, ProtoplasmParams
from modules.audio_reactive.blue_back_n_gray import BlueBackNGrayModule, BlueBackNGrayParams


def shader_test(width: int, height: int) -> ObliquePatch:

    debug_module = DebugModule(
            DebugParams(
                width=width,
                height=height,
            )
        )

    ikeda_test_pattern_module = IkedaTestPatternModule(
        IkedaTestPatternParams(
            width=width,
            height=height,
        )
    )

    protoplasm_module = ProtoplasmModule(
        ProtoplasmParams(
            width=width,
            height=height,
        )
    )

    barrel_distortion_module = BarrelDistortionModule(
        BarrelDistortionParams(
            width=width,
            height=height,
            input_texture=ikeda_test_pattern_module,
        )
    )

    blur_module = BlurModule(
        BlurParams(
            width=width,
            height=height,
            input_texture=barrel_distortion_module,
            blur_amount=1000000.0,
            kernel_size=5,
        )
    )

    feedback_module = FeedbackModule(
        FeedbackParams(
            width=width,
            height=height,
            input_texture=protoplasm_module,
            direction=(0.0, 0.0),
            feedback_strength=0.9,
        )
    )

    mit_particles_module = MITParticlesModule(
        MITParticlesParams(
            width=width,
            height=height
        )
    )

    blue_back_n_gray_module = BlueBackNGrayModule(
        BlueBackNGrayParams(
            width=width,
            height=height,
            strip_offset=50.0,
            n_circles=64,
            # mod_depth=0.6,
            # audio_level=0.8,
        )
    )

    def tick_callback(t: float) -> BaseAVModule:
        blue_back_n_gray_module.params.strip_offset = 50.0 * (sin(t) - 0.5) 
        return blue_back_n_gray_module

    return ObliquePatch(
        tick_callback=tick_callback,
    )


if __name__ == "__main__":
    patch = shader_test(800, 600)
    engine = ObliqueEngine(
        patch=patch,
        width=800,
        height=600,
        title="Shader Test",
        target_fps=60,
        debug=False,
        monitor=None,
    )

    try:
        engine.run()
    except KeyboardInterrupt:
        info("Shutting down...")
    except Exception as e:
        error(f"Engine error: {e}")
        raise
