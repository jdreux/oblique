from typing import Any, Sequence

import numpy as np
from typing_extensions import Dict

from inputs.base_input import BaseInput
from processing.base_processing_operator import BaseProcessingOperator
from core.logger import debug


class FFTBands(BaseProcessingOperator):
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
    """

    metadata: Dict[str, Any] = {
        "name": "FFTBands",
        "description": "Extracts N logarithmically spaced frequency bands from the audio using FFT.",
        "parameters": {"num_bands": int, "sample_rate": int},
    }

    def __init__(self,
                 audio_input: BaseInput,
                 n_fft: int = 4096,
                 num_bands: int = 16,
                 f_min: float = 20.) -> None:

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

        # dB scale parameters
        self.db_floor = -60.0   # silence → 0.0
        self.db_ceil  =   0.0   # full‑scale sine → 1.0
        self.scale = 1.0 / (self.db_ceil - self.db_floor)

        # rolling buffer so caller can feed smaller chunks
        self._ring = np.zeros(n_fft, dtype=np.float32)
        self._write_pos = 0
        self._samples_accumulated = 0  # Track how many samples we've accumulated

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

    def process(self) -> Sequence[float]:
        """
        Feed a new audio chunk and get `n_bands` floats in [0..1].

        Returns 0‑filled bands until the internal buffer holds `n_fft` samples.
        """
        chunk = self.audio_input.peek(n_buffers=1)
        if chunk is None:
            debug("FFT: No audio chunk available")
            return [0.0] * self.n_bands
        
        debug(f"FFT: Got chunk shape {chunk.shape}, samples accumulated: {self._samples_accumulated}")
        self._push_samples(chunk)
        
        # Check if we have enough samples for a full FFT
        if self._samples_accumulated < self.n_fft:
            debug(f"FFT: Not enough samples ({self._samples_accumulated}/{self.n_fft})")
            return [0.0] * self.n_bands

        # windowed FFT
        spectrum = np.fft.rfft(self._ring * self.window)
        mag = np.abs(spectrum)
        
        debug(f"FFT: Spectrum max magnitude: {np.max(mag):.6f}")

        # average magnitude per band
        bands = []
        for b in self.band_bins:
            if b.size > 0:
                band_mag = mag[b].mean()
            else:
                band_mag = 0.0
            bands.append(band_mag)

        # convert to dB (avoid log(0))
        bands = 20 * np.log10(np.maximum(bands, 1e-9))
        debug(f"FFT: Raw bands (first 5): {bands[:5]}")

        # map dB range to 0..1
        bands = (bands - self.db_floor) * self.scale
        result = np.clip(bands, 0.0, 1.0).tolist()
        debug(f"FFT: Final result (first 5): {result[:5]}")
        return result
