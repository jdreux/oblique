import numpy as np
from typing import Any
from .base_processing_operator import BaseProcessingOperator
from inputs.audio_device_input import AudioDeviceInput


class NormalizedAmplitudeOperator(BaseProcessingOperator):
    """
    Computes the normalized amplitude (RMS) of an audio chunk.
    Expects input as a numpy ndarray of shape (chunk_size, channels).
    Returns a float in [0, 1].
    """

    metadata = {
        "name": "NormalizedAmplitudeOperator",
        "description": "Outputs the normalized amplitude (RMS) of an audio chunk.",
        "parameters": {},
    }

    def __init__(self, audio_input: AudioDeviceInput):
        super().__init__()
        self.amplitude = 0.0
        self.audio_input = audio_input

    def process(self) -> float:
        """
        Compute the normalized RMS amplitude of the input audio chunk.
        :param data: np.ndarray, shape (chunk_size, channels)
        :return: float, normalized amplitude in [0, 1]
        """
        data = self.audio_input.peek()
        if data is None:
            return 0.0
        if not isinstance(data, np.ndarray):
            raise ValueError("Input data must be a numpy ndarray.")
        if data.size == 0:
            return 0.0
        # Flatten to mono if multi-channel
        if data.ndim == 2:
            mono = data.mean(axis=1)
        else:
            mono = data
        rms = np.sqrt(np.mean(np.square(mono)))
        # Normalize assuming 16-bit PCM range
        normalized = np.clip(rms / 1.0, 0.0, 1.0)  # 1.0 = max float amplitude
        return float(normalized)


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
    op = NormalizedAmplitudeOperator(input_device)
    for i in range(5):
        chunk = input_device.read()
        amp = op.process()
        print(f"Chunk {i}: normalized amplitude = {amp:.4f}")
    input_device.stop()
