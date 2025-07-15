from core.oblique_patch import ObliquePatch
from inputs.audio_device_input import AudioDeviceInput

# --- Module imports ---
from modules.circle_echo import CircleEcho, CircleEchoParams
from modules.debug import DebugModule, DebugParams
from modules.feedback import Feedback, FeedbackParams
from modules.iked_grid import IkedGrid, IkedGridParams
from modules.ikeda_test_pattern import IkedaTestPatternModule, IkedaTestPatternParams
from modules.ikeda_tiny_barcode import IkedaTinyBarcodeModule, IkedaTinyBarcodeParams
from modules.mesh_shroud import MeshShroudModule, MeshShroudParams
from modules.ryoji_grid import RyojiGrid, RyojiGridParams
from modules.ryoji_lines import RyojiLines, RyojiLinesParams
from modules.shader_toy_tester import ShaderToyTesterModule
from modules.spectral_visualizer import (
    SpectralVisualizerModule,
    SpectralVisualizerParams,
)
from modules.transform import TransformModule, TransformParams
from modules.visual_noise import VisualNoiseModule, VisualNoiseParams
from processing.fft_bands import FFTBands
from processing.normalized_amplitude import NormalizedAmplitudeOperator
from processing.spectral_centroid import SpectralCentroid


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
    patch = ObliquePatch()


    mix_LR = audio_input.get_audio_input_for_channels([0,1])

    patch.input(mix_LR)

    melody = audio_input.get_audio_input_for_channels([2, 9])

    kick_snare = audio_input.get_audio_input_for_channels([10])
    bass = audio_input.get_audio_input_for_channels([12])
    hh = audio_input.get_audio_input_for_channels([13])

    amplitude_processor = NormalizedAmplitudeOperator(kick_snare)
    debug_module = DebugModule(
        DebugParams(width=width, height=height, number=0.0, text="Debug"),
        amplitude_processor,
    )
    # patch.add(debug_module)

    fft_bands_processor16 = FFTBands(melody, num_bands=16)
    ryoji_grid_module = RyojiGrid(RyojiGridParams(width=width, height=height))
    circle_echo_module = CircleEcho(
        CircleEchoParams(width=width, height=height, n_circles=32),
        fft_bands_processor16,
    )

    spectral_centroid_processor = SpectralCentroid(melody)
    fft_bands_processor512 = FFTBands(melody, num_bands=512)
    fft_bands_processor64 = FFTBands(melody, num_bands=64)
    ryoji_lines_module = RyojiLines(
        RyojiLinesParams(width=width, height=height, num_bands=2**7),
        fft_bands_processor512,
        spectral_centroid_processor,
    )
    visual_noise_module = VisualNoiseModule(
        VisualNoiseParams(width=width, height=height, color_mode="rgba", noise_size="large", speed=0.1)
    )
    ikeda_test_pattern = IkedaTestPatternModule(
        IkedaTestPatternParams(width=width, height=height), module=circle_echo_module
    )
    ikeda_tiny_barcode_module = IkedaTinyBarcodeModule(
        IkedaTinyBarcodeParams(width=width, height=height), fft_bands_processor512
    )
    spectral_visualizer_module = SpectralVisualizerModule(
        SpectralVisualizerParams(width=width, height=height), fft_bands_processor512
    )

    mesh_module = MeshShroudModule(
        MeshShroudParams(width=width, height=height), fft_bands_processor64, amplitude_processor
    )

    shader_toy_tester = ShaderToyTesterModule()

    # Create IkedGrid module that creates its own pattern and swaps squares
    iked_grid_module = IkedGrid(
        IkedGridParams(
            width=width,
            height=height,
            grid_size=3,
            swap_frequency=2.0,  # Increased frequency for more visible swaps
            swap_phase=0.0,
            num_swaps=4,
        ),
        module=circle_echo_module,
    )

    # Add feedback module with spectral visualizer as input
    feedback_module = Feedback(
        FeedbackParams(
            width=width,
            height=height,
            feedback_strength=0.95,
            reset_on_start=True,
        ),
        upstream_module=mesh_module,
    )

    # Test transform module
    transform_module = TransformModule(
        TransformParams(
            width=width,
            height=height,
            scale=(0.94, 0.78),
            angle=67,
            pivot=(0.7, 0.3),
            translate=(0.05, -0.5),
            transform_order="SRT",
        ),
        upstream_module=feedback_module,
    )

    # patch.add(shader_toy_tester)  # Test feedback module with input
    # patch.add(spectral_visualizer_module)
    patch.add(spectral_visualizer_module)  # Test transform module
    return patch
