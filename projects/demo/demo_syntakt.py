from core.oblique_patch import ObliquePatch
from inputs.audio_device_input import AudioDeviceInput
from modules.base_av_module import BaseAVModule
from modules.media_module import MediaModule, MediaParams, AspectMode

# --- Module imports ---
from modules.broken_circles import BrokenCirclesModule, BrokenCirclesParams
from modules.pauric_squares_module import PauricSquaresModule, PauricSquaresParams
from modules.composite_module import CompositeModule, CompositeParams
from modules.composite_module import CompositeOp
from processing.envelope import Envelope
from processing.normalized_amplitude import NormalizedAmplitudeOperator


def create_demo_syntakt(width: int, height: int, audio_input: AudioDeviceInput) -> ObliquePatch:
    """
    Create a demo patch with some example modules.
    This is a demo of the Syntakt audio interface.

    Args:
        width: Window width
        height: Window height

    Returns:
        Configured ObliquePatch instance
    """

    mix_LR = audio_input.get_audio_input_for_channels([0, 1])

    t1 = audio_input.get_audio_input_for_channels([2])
    t2 = audio_input.get_audio_input_for_channels([3])
    t3 = audio_input.get_audio_input_for_channels([4])
    t4 = audio_input.get_audio_input_for_channels([5])
    t5 = audio_input.get_audio_input_for_channels([6])
    t8 = audio_input.get_audio_input_for_channels([9])
    t9 = audio_input.get_audio_input_for_channels([10])
    t10 = audio_input.get_audio_input_for_channels([11])
    t11 = audio_input.get_audio_input_for_channels([12])

    a1 = NormalizedAmplitudeOperator(t1)
    a2 = NormalizedAmplitudeOperator(t2)
    a3 = NormalizedAmplitudeOperator(t3)
    a4 = NormalizedAmplitudeOperator(t4)
    a5 = NormalizedAmplitudeOperator(t5)
    a8 = NormalizedAmplitudeOperator(t8)

    a9 = Envelope(NormalizedAmplitudeOperator(t9).process, decay=0.01)
    a10 = Envelope(NormalizedAmplitudeOperator(t10).process, decay=0.1)
    a11 = Envelope(NormalizedAmplitudeOperator(t11).process, decay=0.1)

    broken_circles_module = BrokenCirclesModule(
        BrokenCirclesParams(
            width=width,
            height=height,
            modulators=[a9, a2, a3, a4, a5],
        )
    )

    pauric_squares_module = PauricSquaresModule(
        PauricSquaresParams(
            width=width,
            height=height,
            tile_size=1,
        ),
        motif_module=broken_circles_module,
    )

    media_module = MediaModule(
        MediaParams(
            file_path="./projects/demo/media/banana-alpha.png",
            width=width,
            height=height,
            aspect_mode=AspectMode.PRESERVE,
        ),
    )

    composite_module = CompositeModule(
        CompositeParams(
            width=width,
            height=height,
            operation=CompositeOp.ATOP,
        ),
        top_module=pauric_squares_module,
        bottom_module=media_module,
    )

    def tick_callback(t: float) -> BaseAVModule:
        # respond to bass intensity
        pauric_squares_module.params.tile_size = int(1 + 100 * max(a10.process(), a11.process()))

        print(f"a8: {a8.process()}")

        if a8.process() > 0.001:
            return composite_module
        else:
            return pauric_squares_module

    return ObliquePatch(
        audio_output=mix_LR,
        tick_callback=tick_callback,
    )
