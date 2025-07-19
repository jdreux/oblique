from core.oblique_patch import ObliquePatch
from inputs.audio_device_input import AudioDeviceInput
from core.logger import debug
from modules.base_av_module import P, BaseAVModule

# --- Module imports ---
from modules.circle_echo import CircleEcho, CircleEchoParams
from modules.debug import DebugModule, DebugParams
from modules.feedback import Feedback, FeedbackParams
from modules.grid_swap_module import GridSwapModule, GridSwapModuleParams
from modules.ikeda_tiny_barcode import IkedaTinyBarcodeModule, IkedaTinyBarcodeParams
from modules.mesh_shroud import MeshShroudModule, MeshShroudParams
from modules.ryoji_lines import RyojiLines, RyojiLinesParams
from modules.shader_toy_tester import ShaderToyTesterModule
from modules.spectral_visualizer import (
    SpectralVisualizerModule,
    SpectralVisualizerParams,
)
from modules.transform import TransformModule, TransformParams
from modules.visual_noise import VisualNoiseModule, VisualNoiseParams
from modules.level_module import LevelModule, LevelParams
from processing.fft_bands import FFTBands
from processing.normalized_amplitude import NormalizedAmplitudeOperator
from processing.spectral_centroid import SpectralCentroid
from processing.envelope import Envelope


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


    mix_LR = audio_input.get_audio_input_for_channels([0,1])

    clap = audio_input.get_audio_input_for_channels([4])

    bass_drum = audio_input.get_audio_input_for_channels([10])

    clap_amplitude = NormalizedAmplitudeOperator(clap)

    bass_drum_amplitude = NormalizedAmplitudeOperator(bass_drum)

    bass_drum_envelope = Envelope(bass_drum_amplitude.process)

    clap_counter: int = 0

    fft_bands_processor16 = FFTBands(mix_LR, num_bands=16)

    circle_echo_module = CircleEcho(
        CircleEchoParams(width=width, height=height, n_circles=32),
        fft_bands_processor16,
    )

    grid_swap_module = GridSwapModule(
        GridSwapModuleParams(width=width, height=height, grid_size=16, num_swaps=128),
        circle_echo_module,
    )

    level_module = LevelModule(
        LevelParams(
            invert=False,
        ),
        grid_swap_module,
    )

    def tick_callback(t: float) -> BaseAVModule:

        amplitude: float = clap_amplitude.process()
        bass_intensity: float = bass_drum_envelope.process()

        level_module.params.invert = amplitude > 0.001

        grid_swap_module.params.grid_size = int(16 * bass_intensity*10)
        grid_swap_module.params.num_swaps = int(128 * bass_intensity*10)

        return level_module

    return ObliquePatch(
        audio_output=mix_LR,
        tick_callback=tick_callback,
    )
