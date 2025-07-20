from core.logger import error, info
from core.oblique_engine import ObliqueEngine
from core.oblique_patch import ObliquePatch
from inputs.audio_file_input import AudioFileInput
from modules.base_av_module import BaseAVModule
from modules.debug import DebugModule, DebugParams


def shader_test(width: int, height: int) -> ObliquePatch:

    def tick_callback(t: float) -> BaseAVModule:
        return DebugModule(
            DebugParams(
                width=width,
                height=height,
            )
        )

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
