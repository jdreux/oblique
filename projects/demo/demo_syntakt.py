from core.oblique_patch import ObliquePatch
from inputs.device.elektron.syntakt_device import SyntaktChannel, SyntaktDevice

# --- Module imports ---
from modules.audio_reactive.broken_circles import BrokenCirclesModule, BrokenCirclesParams
from modules.audio_reactive.pauric_squares_module import PauricSquaresModule, PauricSquaresParams
from modules.composition.composite_module import CompositeModule, CompositeOp, CompositeParams
from modules.core.base_av_module import BaseAVModule
from modules.core.media_module import AspectMode, MediaModule, MediaParams
from modules.effects.blur_module import BlurModule, BlurParams
from modules.effects.feedback import FeedbackModule, FeedbackParams
from modules.effects.level_module import LevelModule, LevelParams
from processing.envelope import Envelope
from processing.normalized_amplitude import CurveType, NormalizedAmplitudeOperator


def oblique_patch(width: int, height: int) -> ObliquePatch:
    """
    Create a demo patch with some example modules.
    This is a demo of the Syntakt audio interface.

    Args:
        width: Window width
        height: Window height

    Returns:
        Configured ObliquePatch instance
    """

    syntakt = SyntaktDevice()

    syntakt.start()

    mix_LR = syntakt.get_main_lr_track()

    t1, t2, t3, t4, t5, t8, t9, t10, t11 = [syntakt.get_track(track_number) for track_number in [
        SyntaktChannel.TRACK_1,
        SyntaktChannel.TRACK_2,
        SyntaktChannel.TRACK_3,
        SyntaktChannel.TRACK_4,
        SyntaktChannel.TRACK_5,
        SyntaktChannel.TRACK_8,
        SyntaktChannel.TRACK_9,
        SyntaktChannel.TRACK_10,
        SyntaktChannel.TRACK_11,
    ]]


    a1 = NormalizedAmplitudeOperator(t1)
    a2 = NormalizedAmplitudeOperator(t2)
    a3 = NormalizedAmplitudeOperator(t3)
    a4 = NormalizedAmplitudeOperator(t4)
    a5 = NormalizedAmplitudeOperator(t5)
    a8 = NormalizedAmplitudeOperator(t8)

    a9 = Envelope(NormalizedAmplitudeOperator(t9, curve=CurveType.SIGMOID).process, decay=0.1)
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
            motif_texture=broken_circles_module,
        ),
    )

    media_module = MediaModule(
        MediaParams(
            file_path="./projects/demo/media/banana-alpha.png",
            width=width,
            height=height,
            aspect_mode=AspectMode.PRESERVE,
        ),
    )

    level_module = LevelModule(
        LevelParams(
            width=width,
            height=height,
            parent_module=pauric_squares_module,
        ),
    )

    composite_module = CompositeModule(
        CompositeParams(
            width=width,
            height=height,
            operation=CompositeOp.ATOP,
            top_texture=level_module,
            bottom_texture=media_module,
        ),
    )

    feedback_module = FeedbackModule(
        FeedbackParams(
            width=width,
            height=height,
            feedback_strength=0.5,
            direction=(-0.01, 0.010),
            input_texture=pauric_squares_module,
        ),
    )

    blur_module = BlurModule(
        BlurParams(
            width=width,
            height=height,
            blur_amount=10000,
            input_texture=pauric_squares_module,
        ),
    )

    def tick_callback(t: float) -> BaseAVModule:
        # respond to bass intensity
        pauric_squares_module.params.tile_size = int(1 + 10 * max(a10.process(), a11.process()))

        # print(f"a8: {a8.process()}")

        if a8.process() > 0.001:
            level_module.params.invert = True
            # feedback_module.params.direction = (-feedback_module.params.direction[0], feedback_module.params.direction[1])
            return composite_module
        else:
            level_module.params.invert = False
            return blur_module

    return ObliquePatch(
        audio_output=mix_LR,
        tick_callback=tick_callback,
    )
