import numpy as np
from typing import Any, Dict
from processing.base_processing_operator import BaseProcessingOperator
from inputs.audio_device_input import AudioDeviceInput

class SpectralCentroid(BaseProcessingOperator):
    """
    Computes the spectral centroid (brightness) of the audio signal.
    Returns a float in [0, 1].
    """
    metadata: Dict[str, Any] = {
        "name": "SpectralCentroid",
        "description": "Computes the spectral centroid (brightness) of the audio signal.",
        "parameters": {}
    }

    def __init__(self, audio_input: AudioDeviceInput):
        super().__init__()
        self.audio_input = audio_input

    def process(self) -> float:
        data = self.audio_input.peek()
        if data is None or not isinstance(data, np.ndarray) or data.size == 0:
            return 0.0
        if data.ndim == 2:
            mono = data.mean(axis=1)
        else:
            mono = data
        spectrum = np.abs(np.fft.rfft(mono))
        freqs = np.fft.rfftfreq(len(mono), d=1.0)
        centroid = np.sum(freqs * spectrum) / np.sum(spectrum) if np.sum(spectrum) > 0 else 0.0
        # Normalize by Nyquist frequency
        norm_centroid = centroid / (freqs[-1] if freqs[-1] > 0 else 1.0)
        return float(norm_centroid)

if __name__ == "__main__":
    import sys
    from inputs.audio_device_input import AudioDeviceInput
    file_path = sys.argv[1] if len(sys.argv) > 1 else "../projects/demo/audio/Just takes one try mix even shorter [master]19.06.2025.wav"
    input_device = AudioDeviceInput(file_path, chunk_size=2048)
    input_device.start()
    op = SpectralCentroid(input_device)
    for i in range(5):
        input_device.read()
        print(f"Chunk {i}: spectral centroid = {op.process():.4f}")
    input_device.stop() 