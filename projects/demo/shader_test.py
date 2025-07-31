from core.logger import error, info
from core.oblique_engine import ObliqueEngine
from core.oblique_patch import ObliquePatch
from modules.base_av_module import BaseAVModule
from modules.blur_module import BlurModule, BlurParams
from modules.debug import DebugModule, DebugParams
from modules.feedback import FeedbackModule, FeedbackParams
from modules.ikeda_test_pattern import IkedaTestPatternModule, IkedaTestPatternParams
from modules.protoplasm import ProtoplasmModule, ProtoplasmParams


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

    def tick_callback(t: float) -> BaseAVModule:
        return protoplasm_module

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
