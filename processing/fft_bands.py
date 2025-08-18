from typing import Any, List, Sequence

import numpy as np
from typing_extensions import Dict

from core.logger import debug
from inputs.audio.core.base_audio_input import BaseAudioInput
from processing.base_processing_operator import BaseProcessingOperator


class FFTBands(BaseProcessingOperator[List[float]]):
    """
    Minimal, log‑spaced FFT band analyser for music visualisation.

    Parameters
    ----------
    sample_rate : int
        Audio sample rate in Hz.
    n_fft       : int
        FFT size (power of two). 4096 gives ~10 Hz resolution at 44.1 kHz.
    num_bands     : int
        Number of logarithmic bands to return.
    f_min       : float
        Low‑cut in Hz.
    smoothing_factor : float
        Exponential moving average smoothing factor (0.0 to 1.0).
        Controls how much smoothing is applied to reduce jumpiness:
        - 0.0: No smoothing (very jumpy, immediate response)
        - 0.1: Heavy smoothing (very smooth, slow response)
        - 0.3: Moderate smoothing (balanced, default)
        - 0.5: Light smoothing (responsive but smooth)
        - 1.0: No smoothing (same as 0.0)
        Lower values = more smoothing, higher values = less smoothing.
    """

    metadata: Dict[str, Any] = {
        "name": "FFTBands",
        "description": "Extracts N logarithmically spaced frequency bands from the audio using FFT.",
        "parameters": {"num_bands": int, "sample_rate": int},
    }

    def __init__(self,
                 audio_input: BaseAudioInput,
                 n_fft: int = 4096,
                 num_bands: int = 16,
                 f_min: float = 20.,
                 smoothing_factor: float = 0.3) -> None:

        self.audio_input = audio_input
        self.sample_rate = audio_input.sample_rate
        self.n_fft     = n_fft
        self.n_bands   = num_bands
        self.f_min     = f_min
        self.f_max     = self.sample_rate / 2
        self.window    = np.hanning(n_fft).astype(np.float32)

        # pre‑compute bin indices for each band
        freqs   = np.fft.rfftfreq(n_fft, 1 / self.sample_rate)
        edges   = np.logspace(np.log10(f_min),
                              np.log10(self.f_max),
                              num_bands + 1)

        # Calculate band bins and handle empty bands
        self.band_bins = []
        for i in range(num_bands):
            band_bins = np.where((freqs >= edges[i]) & (freqs < edges[i+1]))[0]
            if band_bins.size == 0:
                # If band is empty, find the closest frequency bin
                center_freq = np.sqrt(edges[i] * edges[i+1])  # geometric mean
                closest_idx = np.argmin(np.abs(freqs - center_freq))
                band_bins = np.array([closest_idx])
            self.band_bins.append(band_bins)

        # dB scale parameters - much more conservative for electronic music
        self.db_floor = -60.0  # silence → 0.0 (much lower floor)
        self.db_ceil  = 60.0   # full‑scale sine → 1.0 (much lower ceiling)
        self.scale = 1.0 / (self.db_ceil - self.db_floor)

        # rolling buffer so caller can feed smaller chunks
        self._ring = np.zeros(n_fft, dtype=np.float32)
        self._write_pos = 0
        self._samples_accumulated = 0  # Track how many samples we've accumulated

        # Smoothing parameters
        self._smoothed_bands = None  # Will store the smoothed values
        self._smoothing_factor = smoothing_factor  # How much to smooth (0.0 = no smoothing, 1.0 = max smoothing)

    # -------------------------------------------------------------

    def _push_samples(self, chunk: np.ndarray) -> None:
        """Append mono samples into the ring buffer."""
        if chunk.ndim == 2:
            chunk = chunk.mean(axis=1)

        n = len(chunk)
        if n == 0:
            return

        # Handle the case where chunk is larger than ring buffer
        if n >= self.n_fft:
            # Keep only the last n_fft samples
            chunk = chunk[-self.n_fft:]
            n = self.n_fft

        # Write to ring buffer
        for i in range(n):
            pos = (self._write_pos + i) % self.n_fft
            self._ring[pos] = chunk[i]

        self._write_pos = (self._write_pos + n) % self.n_fft
        self._samples_accumulated = min(self._samples_accumulated + n, self.n_fft)

    def process(self) -> List[float]:
        """
        Feed a new audio chunk and get `n_bands` floats in [0..1].

        Returns 0‑filled bands until the internal buffer holds `n_fft` samples.
        """
        chunk = self.audio_input.peek(n_buffers=1)
        if chunk is None:
            # debug("FFT: No audio chunk available")
            return [0.0] * self.n_bands

        self._push_samples(chunk)

        # Check if we have enough samples for a full FFT
        if self._samples_accumulated < self.n_fft:
            debug(f"FFT: Not enough samples ({self._samples_accumulated}/{self.n_fft})")
            return [0.0] * self.n_bands

        # windowed FFT
        spectrum = np.fft.rfft(self._ring * self.window)
        mag = np.abs(spectrum)

        # average magnitude per band
        bands = []
        for b in self.band_bins:
            if b.size > 0:
                band_mag = mag[b].mean()
            else:  # pragma: no cover - band bins precomputed to be non-empty
                band_mag = 0.0
            bands.append(band_mag)

        # convert to dB (avoid log(0))
        bands = 20 * np.log10(np.maximum(bands, 1e-9))

        # map dB range to 0..1
        bands = (bands - self.db_floor) * self.scale
        result = np.clip(bands, 0.0, 1.0)

        # Apply smoothing
        if self._smoothed_bands is None:
            self._smoothed_bands = result.copy()
        else:
            # Exponential moving average: new = alpha * current + (1-alpha) * previous
            self._smoothed_bands = (self._smoothing_factor * result +
                                   (1.0 - self._smoothing_factor) * self._smoothed_bands)

        return self._smoothed_bands.tolist()
