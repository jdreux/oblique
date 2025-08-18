
import numpy as np
from typing import Optional
from enum import Enum, auto

from inputs.audio.core.base_audio_input import BaseAudioInput

from .base_processing_operator import BaseProcessingOperator


class CurveType(Enum):
    NONE = auto()
    SQRT = auto()
    LOG = auto()
    SIGMOID = auto()


class NormalizedAmplitudeOperator(BaseProcessingOperator[float]):
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

    def __init__(self, audio_input: BaseAudioInput, curve: CurveType = CurveType.NONE):
        """
        :param audio_input: BaseAudioInput providing audio data
        :param curve: Optional non-linear mapping (CurveType)
        """
        super().__init__()
        self.amplitude = 0.0
        self.audio_input = audio_input
        self.curve = curve

    def process(self) -> float:
        """
        Compute the normalized RMS amplitude of the input audio chunk, mapped to [0, 1] using dBFS.
        Optionally applies a non-linear curve for perceptual scaling.
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
        if rms < 1e-10:
            return 0.0
        dbfs = 20 * np.log10(rms)
        # Map -60 dBFS (quiet) to 0, 0 dBFS (max) to 1
        normalized = np.clip((dbfs + 60) / 60, 0.0, 1.0)
        # Optional non-linear mapping
        if self.curve == CurveType.SQRT:
            normalized = np.sqrt(normalized)
        elif self.curve == CurveType.LOG:
            normalized = np.log1p(9 * normalized) / np.log1p(9)  # log curve, 0-1
        elif self.curve == CurveType.SIGMOID:
            normalized = 1 / (1 + np.exp(-8 * (normalized - 0.5)))  # sigmoid centered at 0.5
        return float(normalized)


if __name__ == "__main__":  # pragma: no cover
    import sys

    from inputs.audio.core.audio_file_input import AudioFileInput

    file_path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "../projects/demo/audio/Just takes one try mix even shorter [master]19.06.2025.wav"
    )
    input_device = AudioFileInput(file_path, chunk_size=2048)
    input_device.start()
    op = NormalizedAmplitudeOperator(input_device, curve=CurveType.SQRT)
    for i in range(5):
        chunk = input_device.read()
        amp = op.process()
        print(f"Chunk {i}: normalized amplitude = {amp:.4f}")
    input_device.stop()
