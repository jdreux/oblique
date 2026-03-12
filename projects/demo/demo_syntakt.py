from core.oblique_patch import ObliquePatch
from inputs.device.elektron.syntakt_device import SyntaktChannel, SyntaktDevice

from modules.audio_reactive.broken_circles import BrokenCirclesModule, BrokenCirclesParams
from modules.audio_reactive.pauric_squares_module import PauricSquaresModule
from modules.composition.composite_module import CompositeOp
from modules.core.base_av_module import BaseAVModule
from modules.core.media_module import AspectMode, MediaModule, MediaParams
from modules.effects.blur_module import BlurModule
from modules.effects.feedback import FeedbackModule
from modules.effects.level_module import LevelModule
from processing.envelope import Envelope
from processing.normalized_amplitude import CurveType, NormalizedAmplitudeOperator


def oblique_patch(width: int, height: int) -> ObliquePatch:
    """
    Create a demo patch with some example modules.
    This is a demo of the Syntakt audio interface.
    """

    syntakt = SyntaktDevice()
    syntakt.start()

    mix_LR = syntakt.get_main_lr_track()

    t1, t2, t3, t4, t5, t8, t9, t10, t11 = [
        syntakt.get_track(track_number)
        for track_number in [
            SyntaktChannel.TRACK_1,
            SyntaktChannel.TRACK_2,
            SyntaktChannel.TRACK_3,
            SyntaktChannel.TRACK_4,
            SyntaktChannel.TRACK_5,
            SyntaktChannel.TRACK_8,
            SyntaktChannel.TRACK_9,
            SyntaktChannel.TRACK_10,
            SyntaktChannel.TRACK_11,
        ]
    ]

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

    media_module = MediaModule(
        MediaParams(
            file_path="projects/demo/media/banana-alpha.png",
            width=width,
            height=height,
            aspect_mode=AspectMode.PRESERVE,
        ),
    )

    # --- Effect chains using .to() / .mix() ---

    pauric_squares_module = broken_circles_module.to(PauricSquaresModule, tile_size=1)

    level_module = pauric_squares_module.to(LevelModule)

    composite_module = level_module.mix(media_module, op=CompositeOp.ATOP)

    feedback_module = pauric_squares_module.to(
        FeedbackModule, feedback_strength=0.5, direction=(-0.01, 0.010)
    )

    blur_module = pauric_squares_module.to(BlurModule, blur_amount=10000)

    def tick_callback(t: float) -> BaseAVModule:
        pauric_squares_module.params.tile_size = int(
            1 + 10 * max(a10.process(), a11.process())
        )

        if a8.process() > 0.001:
            level_module.params.invert = True
            return composite_module
        else:
            level_module.params.invert = False
            return blur_module

    return ObliquePatch(
        audio_output=mix_LR,
        tick_callback=tick_callback,
    )
