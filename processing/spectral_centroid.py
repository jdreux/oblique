from typing import Any, Dict

import numpy as np

from inputs.audio.core.base_audio_input import BaseAudioInput
from processing.base_processing_operator import BaseProcessingOperator


class SpectralCentroid(BaseProcessingOperator[float]):
    """
    Computes the spectral centroid (brightness) of the audio signal.
    Returns a float in [0, 1] humanized for techno music.
    """

    metadata: Dict[str, Any] = {
        "name": "SpectralCentroid",
        "description": "Computes the spectral centroid (brightness) of the audio signal, humanized for techno music.",
        "parameters": {},
    }

    def __init__(self, audio_input: BaseAudioInput):
        super().__init__()
        self.audio_input = audio_input
        # Techno music typically has meaningful brightness content up to ~8kHz
        # We'll use this as our "bright" reference instead of Nyquist
        self.bright_freq_threshold = 8000.0  # Hz
        self.sample_rate = 44100.0

    def process(self) -> float:
        data = self.audio_input.peek()
        if data is None or not isinstance(data, np.ndarray) or data.size == 0:
            return 0.0

        if data.ndim == 2:
            mono = data.mean(axis=1)
        else:
            mono = data

        spectrum = np.abs(np.fft.rfft(mono))
        freqs = np.fft.rfftfreq(len(mono), d=1.0 / self.sample_rate)

        # Calculate raw centroid
        centroid = (
            np.sum(freqs * spectrum) / np.sum(spectrum) if np.sum(spectrum) > 0 else 0.0
        )

        # Humanize the centroid for techno music:
        # 1. Normalize by our "bright" threshold instead of Nyquist
        # 2. Apply a non-linear curve that emphasizes the musically relevant range
        # 3. Clamp to [0, 1] with a curve that makes "bright" techno closer to 1

        # Normalize by bright threshold (8kHz for techno)
        norm_centroid = centroid / self.bright_freq_threshold

        # Apply non-linear mapping to emphasize musically relevant brightness
        # This curve makes:
        # - 0-2kHz (bass/kick range): maps to 0-0.3
        # - 2-4kHz (mid range): maps to 0.3-0.6
        # - 4-8kHz (bright range): maps to 0.6-1.0
        # - >8kHz: saturates towards 1.0

        if norm_centroid <= 0.25:  # 0-2kHz range
            humanized = norm_centroid * 1.2  # Gentle slope for bass
        elif norm_centroid <= 0.5:  # 2-4kHz range
            humanized = 0.3 + (norm_centroid - 0.25) * 1.2  # Steeper for mids
        elif norm_centroid <= 1.0:  # 4-8kHz range
            humanized = 0.6 + (norm_centroid - 0.5) * 0.8  # Steep for bright
        else:  # >8kHz
            humanized = 1.0 - np.exp(-(norm_centroid - 1.0) * 0.5)  # Saturate

        # Ensure we stay in [0, 1] range
        humanized = np.clip(humanized, 0.0, 1.0)

        return float(humanized)


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
    op = SpectralCentroid(input_device)
    for i in range(5):
        input_device.read()
        print(f"Chunk {i}: spectral centroid = {op.process():.4f}")
    input_device.stop()
