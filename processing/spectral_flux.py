import numpy as np
from typing import Any, Dict
from processing.base_processing_operator import BaseProcessingOperator
from inputs.audio_device_input import AudioDeviceInput


class SpectralFlux(BaseProcessingOperator):
    """
    Computes the spectral flux (rate of change in the spectrum) of the audio signal.
    Returns a float >= 0.
    """

    metadata: Dict[str, Any] = {
        "name": "SpectralFlux",
        "description": "Computes the spectral flux (rate of change in the spectrum) of the audio signal.",
        "parameters": {},
    }

    def __init__(self, audio_input: AudioDeviceInput):
        super().__init__()
        self.audio_input = audio_input
        self.prev_spectrum = None

    def process(self) -> float:
        data = self.audio_input.peek()
        if data is None or not isinstance(data, np.ndarray) or data.size == 0:
            return 0.0
        if data.ndim == 2:
            mono = data.mean(axis=1)
        else:
            mono = data
        spectrum = np.abs(np.fft.rfft(mono))
        if self.prev_spectrum is None:
            self.prev_spectrum = spectrum
            return 0.0
        flux = np.sqrt(np.sum((spectrum - self.prev_spectrum) ** 2)) / len(spectrum)
        self.prev_spectrum = spectrum
        return float(flux)


if __name__ == "__main__":
    import sys
    from inputs.audio_device_input import AudioDeviceInput

    file_path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "../projects/demo/audio/Just takes one try mix even shorter [master]19.06.2025.wav"
    )
    input_device = AudioDeviceInput(file_path, chunk_size=2048)
    input_device.start()
    op = SpectralFlux(input_device)
    for i in range(5):
        input_device.read()
        print(f"Chunk {i}: spectral flux = {op.process():.4f}")
    input_device.stop()
