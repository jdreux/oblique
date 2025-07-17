from core.oblique_patch import ObliquePatch
from inputs.audio_file_input import AudioFileInput
from modules.circle_echo import CircleEcho, CircleEchoParams
from modules.grid_swap_module import GridSwapModule, GridSwapModuleParams
from modules.ryoji_lines import RyojiLines, RyojiLinesParams
from modules.ikeda_tiny_barcode import IkedaTinyBarcodeModule, IkedaTinyBarcodeParams
from modules.spectral_visualizer import SpectralVisualizerModule, SpectralVisualizerParams
from processing.fft_bands import FFTBands
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

    patch = ObliquePatch()

    audio_input = AudioFileInput(
        file_path="projects/demo/audio/Just takes one try mix even shorter [master]19.06.2025.wav"
    )

    patch.input(audio_input)

    fft_bands_processor16 = FFTBands(audio_input, num_bands=16)
    fft_bands_processor512 = FFTBands(audio_input, num_bands=512)
    spectral_centroid_processor = SpectralCentroid(audio_input)
    # fft_bands_processor64 = FFTBands(audio_input, perceptual=True, num_bands=64)

    ikeda_tiny_barcode_module = IkedaTinyBarcodeModule(
        IkedaTinyBarcodeParams(width=width, height=height), fft_bands_processor512
    )
    spectral_visualizer_module = SpectralVisualizerModule(
        SpectralVisualizerParams(width=width, height=height), fft_bands_processor512
    )

    grid_swap_module = GridSwapModule(
        GridSwapModuleParams(
            width=width,
            height=height,
            grid_size=16,
            swap_frequency=2.0,  # Increased frequency for more visible swaps
            swap_phase=0.0,
            num_swaps=128,
        ),
        module=spectral_visualizer_module,
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

    patch.add(ryoji_lines_module)  # Test transform module
    return patch
