from core.oblique_patch import ObliquePatch
from inputs.audio_file_input import AudioFileInput
from modules.ikeda_tiny_barcode import IkedaTinyBarcodeModule, IkedaTinyBarcodeParams
from processing.fft_bands import FFTBands


def audio_file_demo_patch(width: int, height: int) -> ObliquePatch:
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

    audio_input = AudioFileInput(file_path="projects/demo/audio/Just takes one try mix even shorter [master]19.06.2025.wav")

    patch.input(audio_input)


    fft_bands_processor512 = FFTBands(audio_input, perceptual=True, num_bands=512)
    fft_bands_processor64 = FFTBands(audio_input, perceptual=True, num_bands=64)

    ikeda_tiny_barcode_module = IkedaTinyBarcodeModule(
        IkedaTinyBarcodeParams(width=width, height=height), fft_bands_processor512
    )

    patch.add(ikeda_tiny_barcode_module)  # Test transform module
    return patch



