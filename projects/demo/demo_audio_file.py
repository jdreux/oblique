from core.oblique_patch import ObliquePatch
from inputs.audio.core.audio_file_input import AudioFileInput
from modules.audio_reactive.circle_echo import CircleEcho, CircleEchoParams
from modules.audio_reactive.grid_swap_module import GridSwapModule
from modules.audio_reactive.ikeda_tiny_barcode import IkedaTinyBarcodeModule, IkedaTinyBarcodeParams
from modules.audio_reactive.mit_particles import MITParticlesModule, MITParticlesParams
from modules.audio_reactive.pauric_squares_module import PauricSquaresModule
from modules.audio_reactive.ryoji_lines import RyojiLines, RyojiLinesParams
from modules.audio_reactive.spectral_visualizer import SpectralVisualizerModule, SpectralVisualizerParams
from modules.composition.composite_module import CompositeOp
from modules.core.base_av_module import BaseAVModule
from modules.core.media_module import AspectMode, MediaModule, MediaParams
from modules.effects.barrel_distortion import BarrelDistortionModule
from modules.effects.feedback import FeedbackModule
from modules.effects.level_module import LevelModule
from modules.utility.transform import TransformModule
from processing.fft_bands import FFTBands
from processing.normalized_amplitude import NormalizedAmplitudeOperator
from processing.spectral_centroid import SpectralCentroid


def oblique_patch(width: int, height: int) -> ObliquePatch:  # type: ignore
    """
    Create a demo patch with some example modules.
    This is a demo of the audio input from file
    """

    audio_input = AudioFileInput(
        file_path="projects/demo/audio/Just takes one try mix even shorter [master]19.06.2025.wav"
    )

    fft_bands_processor16 = FFTBands(audio_input, num_bands=16)
    fft_bands_processor512 = FFTBands(audio_input, num_bands=512)
    spectral_centroid_processor = SpectralCentroid(audio_input)

    # --- Source generators (take extra constructor args, not chainable targets) ---

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

    media_module = MediaModule(
        MediaParams(
            file_path="projects/demo/media/banana-alpha.png",
            width=width,
            height=height,
            aspect_mode=AspectMode.PRESERVE,
        )
    )

    # --- Effect chain using .to() / .mix() ---

    composite_transform = (
        ryoji_lines_module
        .to(PauricSquaresModule)
        .to(TransformModule, transform_order="SRT")
        .to(BarrelDistortionModule)
        .to(GridSwapModule, grid_size=0, swap_frequency=2.0, swap_phase=0.0, num_swaps=128)
        .to(FeedbackModule, feedback_strength=0.9)
        .to(LevelModule, invert=True)
        .mix(media_module, op=CompositeOp.ATOP)
        .to(FeedbackModule, feedback_strength=0, direction=(0.0, -0.001))
        .to(TransformModule, transform_order="SRT")
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

        mit_particles_module.params.noise_strength = amplitude
        mit_particles_module.params.gravity_strength = amplitude
        mit_particles_module.params.swirl_strength = amplitude
        mit_particles_module.params.circle_radius = amplitude
        return composite_transform

    return ObliquePatch(audio_output=audio_input, tick_callback=_tick_callback)
