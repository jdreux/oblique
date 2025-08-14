import math

from core.oblique_patch import ObliquePatch
from inputs.audio_file_input import AudioFileInput
from modules.audio_reactive.mit_particles import MITParticlesModule, MITParticlesParams
from modules.effects.barrel_distortion import BarrelDistortionModule, BarrelDistortionParams
from modules.composition.composite_module import CompositeModule, CompositeParams, CompositeOp
from modules.core.base_av_module import BaseAVModule
from modules.audio_reactive.circle_echo import CircleEcho, CircleEchoParams
from modules.effects.feedback import FeedbackModule, FeedbackParams
from modules.audio_reactive.grid_swap_module import GridSwapModule, GridSwapModuleParams
from modules.audio_reactive.ikeda_tiny_barcode import IkedaTinyBarcodeModule, IkedaTinyBarcodeParams
from modules.effects.level_module import LevelModule, LevelParams
from modules.core.media_module import AspectMode, MediaModule, MediaParams
from modules.audio_reactive.pauric_squares_module import PauricSquaresModule, PauricSquaresParams
from modules.audio_reactive.ryoji_lines import RyojiLines, RyojiLinesParams
from modules.audio_reactive.spectral_visualizer import SpectralVisualizerModule, SpectralVisualizerParams
from modules.utility.transform import TransformModule, TransformParams
from processing.fft_bands import FFTBands
from processing.normalized_amplitude import NormalizedAmplitudeOperator
from processing.spectral_centroid import SpectralCentroid



def audio_file_demo_patch(width: int, height: int) -> ObliquePatch: # type: ignore
    """
    Create a demo patch with some example modules.
    This is a demo of the audio input from file

    Args:
        width: Window width
        height: Window height

    Returns:
        Configured ObliquePatch instance
    """



    audio_input = AudioFileInput(
        file_path="projects/demo/audio/Just takes one try mix even shorter [master]19.06.2025.wav"
    )

    fft_bands_processor16 = FFTBands(audio_input, num_bands=16)
    fft_bands_processor512 = FFTBands(audio_input, num_bands=512)
    spectral_centroid_processor = SpectralCentroid(audio_input)
    # fft_bands_processor64 = FFTBands(audio_input, perceptual=True, num_bands=64)

    ikeda_tiny_barcode_module = IkedaTinyBarcodeModule(
        IkedaTinyBarcodeParams(fft_bands=fft_bands_processor512, width=width, height=height),
    )
    spectral_visualizer_module = SpectralVisualizerModule(
        SpectralVisualizerParams(width=width, height=height), fft_bands_processor512
    )


    ryoji_lines_module = RyojiLines(
        RyojiLinesParams(width=width, height=height, num_bands=2**7),
        fft_bands_processor512,
        spectral_centroid_processor,
    )
    circle_echo_module = CircleEcho(
        CircleEchoParams(width=width, height=height, n_circles=32),
        fft_bands_processor16,
    )

    # normalized_amplitude_processor = NormalizedAmplitudeOperator(audio_input)

    pauric_squares_module = PauricSquaresModule(
        PauricSquaresParams(
            width=width,
            height=height,
            motif_texture=ryoji_lines_module,
        ),
    )

    transform_module = TransformModule(
        TransformParams(
            width=width,
            height=height,
            # scale=(1.0, 1.0),
            # angle=0.0,
            # pivot=(0.5, 0.5),
            # translate=(0.0, 0.0),
            transform_order="SRT",
            input_texture=pauric_squares_module,
        ),
    )





    barrel_distortion_module = BarrelDistortionModule(
        BarrelDistortionParams(
            width=width,
            height=height,
            input_texture=transform_module,
        ),
    )

    grid_swap_module = GridSwapModule(
        GridSwapModuleParams(
            width=width,
            height=height,
            grid_size=0,
            swap_frequency=2.0,  # Increased frequency for more visible swaps
            swap_phase=0.0,
            num_swaps=128,
            swapped_texture=barrel_distortion_module,
        ),
    )


    feedback_module = FeedbackModule(
        FeedbackParams(
            width=width,
            height=height,
            feedback_strength=0.9,
            input_texture=grid_swap_module,
        ),
    )

    level_module = LevelModule(
        LevelParams(
            width=width,
            height=height,
            parent_module=feedback_module,
            invert=True,
        ),
    )

    media_module = MediaModule(
        MediaParams(
            file_path="./projects/demo/media/banana-alpha.png",
            width=width,
            height=height,
            aspect_mode=AspectMode.PRESERVE,
        )
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

    composite_feedback = FeedbackModule(
        FeedbackParams(
            width=width,
            height=height,
            feedback_strength=0,
            direction=(0.0, -0.001),
            input_texture=composite_module,
        ),
    )

    composite_transform = TransformModule(
        TransformParams(
            width=width,
            height=height,
            transform_order="SRT",
            input_texture=composite_feedback,
        ),
    )

    mit_particles_module = MITParticlesModule(
        MITParticlesParams(
            width=width,
            height=height,
            num_particles=500,
        ),
    ) 


    normalized_amplitude_processor = NormalizedAmplitudeOperator(audio_input)

    def _tick_callback(t: float) -> BaseAVModule:
        amplitude: float = normalized_amplitude_processor.process() * 550.0


        # grid_swap_module.params.grid_size = int(16 * amplitude)
        # grid_swap_module.params.num_swaps = int(128 * amplitude)

        # #slide content vertically over time
        # transform_module.params.translate = (math.sin(t * 2.0)*0.1, 0.0)
        # feedback_module.params.direction = (0.0, -0.001)
        # pauric_squares_module.params.tile_size = int(2 + 8000 * amplitude)
        # # level_module.params.invert = t % 4 <

        # barrel_distortion_module.params.strength = -(0.5 + 5 * amplitude)
        # barrel_distortion_module.params.center = (0.5 * math.sin(t * 2.0), 0.5 * math.sin(t * 2.0))

        # if t*10 % 95 < 5:
        #     level_module.params.invert = True
        # else:
        #     level_module.params.invert = False
        # # print(f"Grid size: {grid_swap_module.params.grid_size}, Num swaps: {grid_swap_module.params.num_swaps}")

        # composite_transform.params.angle = t * 10
        mit_particles_module.params.noise_strength = amplitude
        mit_particles_module.params.gravity_strength = amplitude
        mit_particles_module.params.swirl_strength = amplitude
        mit_particles_module.params.circle_radius = amplitude
        # mit_particles_module.params.num_particles = int(100 * amplitude)
        return mit_particles_module


    return ObliquePatch(audio_output=audio_input, tick_callback=_tick_callback)
