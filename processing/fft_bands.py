import numpy as np
from typing import Any, Dict, List, Optional
from processing.base_processing_operator import BaseProcessingOperator
from inputs.audio_device_input import AudioDeviceInput


class FFTBands(BaseProcessingOperator):
    """
    Extracts N logarithmically spaced frequency bands from the audio using FFT.
    Expects input as a numpy ndarray of shape (chunk_size, channels).
    Returns a list of band amplitudes.
    Bands are distributed logarithmically from 20 Hz to Nyquist (sample_rate/2),
    which is optimal for electronic music (bass, mids, highs, etc).
    """

    metadata: Dict[str, Any] = {
        "name": "FFTBands",
        "description": "Extracts N logarithmically spaced frequency bands from the audio using FFT.",
        "parameters": {"num_bands": int, "sample_rate": int},
    }

    def __init__(
        self,
        audio_input: AudioDeviceInput,
        num_bands: int = 16,
        sample_rate: int = 44100,
        perceptual: bool = False,
        gamma: float = 0.3,
        high_boost: float = 0.7,
    ):
        """
        Args:
            audio_input (AudioDeviceInput): Audio input source.
            num_bands (int): Number of frequency bands.
            sample_rate (int): Audio sample rate.
            perceptual (bool): If True, apply perceptual scaling to band amplitudes.
            gamma (float): Power-law compression factor (<1 boosts low amplitudes).
            high_boost (float): Amount to boost higher bands (0 = none, 1 = strong).
        """
        super().__init__()
        self.audio_input = audio_input
        self.num_bands = num_bands
        self.sample_rate = sample_rate
        self.f_min = 20.0  # Minimum frequency for bands (Hz)
        self.f_max = sample_rate / 2  # Nyquist
        self.band_edges = None  # Will be computed on first process
        self.perceptual = perceptual
        self.gamma = gamma
        self.high_boost = high_boost

    def _compute_band_edges(self, fft_size: int) -> List[np.ndarray]:
        """
        Compute the FFT bin indices for each logarithmic band.
        Returns a list of arrays, each containing the bin indices for a band.
        """
        # Logarithmically spaced band edges
        edges = np.logspace(
            np.log10(self.f_min), np.log10(self.f_max), self.num_bands + 1
        )
        # FFT bin center frequencies
        freqs = np.fft.rfftfreq(fft_size, 1 / self.sample_rate)
        # For each band, find the bin indices
        band_bins = [
            np.where((freqs >= edges[i]) & (freqs < edges[i + 1]))[0]
            for i in range(self.num_bands)
        ]
        return band_bins

    def _perceptual_scale(self, bands: List[float]) -> List[float]:
        """
        Apply perceptual scaling: power-law compression and high-frequency boost.
        No dynamic normalization—output remains in [0, 1] range.
        This avoids boosting quiet signals and keeps scaling static, since bands are already normalized.
        """
        # Power-law compression (gamma < 1 boosts low amplitudes)
        scaled = [b**self.gamma for b in bands]
        # High-frequency boost
        n = len(scaled)
        boosted = (
            [v * (1 + self.high_boost * (i / (n - 1))) for i, v in enumerate(scaled)]
            if n > 1
            else scaled
        )
        # Clip to [0, 1]
        return [min(max(v, 0.0), 1.0) for v in boosted]

    def process(self) -> List[float]:
        """
        Process the current audio chunk and return normalized band amplitudes.
        Each band amplitude is normalized by the theoretical maximum FFT magnitude for a full-scale sine wave (amplitude 1.0), which is (fft_size / 2) for a real-valued sine wave at a single frequency.
        The result is clipped to [0, 1].
        If perceptual is True, applies perceptual scaling to the bands.
        """
        # Use up to 4 most recent buffers for higher FFT resolution (improves low-frequency band coverage)
        data = self.audio_input.peek(n_buffers=4)
        if data is None or not isinstance(data, np.ndarray) or data.size == 0:
            return [0.0] * self.num_bands
        if data.ndim == 2:
            mono = data.mean(axis=1)
        else:
            mono = data
        fft = np.abs(np.fft.rfft(mono))
        fft_size = len(mono)
        # Recompute band edges if fft_size changes
        if self.band_edges is None:
            self.band_edges = self._compute_band_edges(fft_size)

        # Compute FFT
        fft = np.abs(np.fft.rfft(mono))

        bands = []
        # Theoretical max FFT magnitude for a full-scale sine wave (amplitude 1.0)
        max_fft_magnitude = fft_size / 2.0
        for bins in self.band_edges:
            if len(bins) == 0:
                bands.append(0.0)
            else:
                # Use mean for better stability, but consider using max for more responsive peaks
                band_amp = float(np.mean(fft[bins]))
                # Normalize and clip to [0, 1]
                normalized = np.clip(band_amp / max_fft_magnitude, 0.0, 1.0)
                bands.append(normalized)
        if self.perceptual:
            bands = self._perceptual_scale(bands)
        return bands


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
    op = FFTBands(input_device, num_bands=8, sample_rate=44100)
    for i in range(5):
        input_device.read()
        bands = op.process()
        print(f"Chunk {i}: bands = {bands}")
    input_device.stop()
