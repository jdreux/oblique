import numpy as np
from typing import Any, Dict
from processing.base_processing_operator import BaseProcessingOperator
from inputs.audio_device_input import AudioDeviceInput

class ZeroCrossingRate(BaseProcessingOperator):
    """
    Computes the zero crossing rate of the audio signal.
    Returns the rate as a float in [0, 1].
    """
    metadata: Dict[str, Any] = {
        "name": "ZeroCrossingRate",
        "description": "Computes the zero crossing rate of the audio signal.",
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
        zero_crossings = np.where(np.diff(np.signbit(mono)))[0]
        rate = len(zero_crossings) / len(mono) if len(mono) > 0 else 0.0
        return float(rate)

if __name__ == "__main__":
    import sys
    from inputs.audio_device_input import AudioDeviceInput
    file_path = sys.argv[1] if len(sys.argv) > 1 else "../projects/demo/audio/Just takes one try mix even shorter [master]19.06.2025.wav"
    input_device = AudioDeviceInput(file_path, chunk_size=2048)
    input_device.start()
    op = ZeroCrossingRate(input_device)
    for i in range(5):
        input_device.read()
        print(f"Chunk {i}: zero crossing rate = {op.process():.4f}")
    input_device.stop() 