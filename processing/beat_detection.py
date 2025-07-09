import numpy as np
from typing import Any, Dict
from processing.base_processing_operator import BaseProcessingOperator
from inputs.audio_device_input import AudioDeviceInput


class BeatDetection(BaseProcessingOperator):
    """
    Simple energy-based beat/onset detection.
    Returns True if a beat is detected in the current chunk.
    """

    metadata: Dict[str, Any] = {
        "name": "BeatDetection",
        "description": "Simple energy-based beat/onset detection.",
        "parameters": {"threshold": float},
    }

    def __init__(self, audio_input: AudioDeviceInput, threshold: float = 1.5):
        super().__init__()
        self.audio_input = audio_input
        self.threshold = threshold
        self.prev_energy = 0.0

    def process(self) -> bool:
        data = self.audio_input.peek()
        if data is None or not isinstance(data, np.ndarray) or data.size == 0:
            return False
        if data.ndim == 2:
            mono = data.mean(axis=1)
        else:
            mono = data
        energy = np.sum(mono**2)
        beat = (
            energy > self.threshold * self.prev_energy
            if self.prev_energy > 0
            else False
        )
        self.prev_energy = energy
        return beat


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
    op = BeatDetection(input_device, threshold=1.5)
    for i in range(5):
        input_device.read()
        print(f"Chunk {i}: beat = {op.process()}")
    input_device.stop()
