"""
Audio feature extraction for Oblique.
Extracts FFT bands, envelopes, peaks, and other audio features.
"""

import numpy as np
from typing import Dict, List, Any
import time


class AudioFeatureExtractor:
    """Extract meaningful audio features from raw audio data."""
    
    def __init__(self, fft_size: int = 64, sample_rate: int = 44100):
        """Initialize the feature extractor."""
        self.fft_size = fft_size
        self.sample_rate = sample_rate
        self.history_size = 10
        self.peak_history = []
        self.envelope_history = []
        
    def extract_features(self, audio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract features from raw audio data."""
        features = {}
        
        # Extract FFT bands
        if 'fft' in audio_data:
            features['fft_bands'] = self._normalize_fft(audio_data['fft'])
            features['fft_centroid'] = self._calculate_spectral_centroid(audio_data['fft'])
            features['fft_rolloff'] = self._calculate_spectral_rolloff(audio_data['fft'])
        
        # Extract envelope and peak
        if 'env' in audio_data:
            features['envelope'] = self._smooth_envelope(audio_data['env'])
        
        if 'peak' in audio_data:
            features['peak'] = self._smooth_peak(audio_data['peak'])
        
        # Calculate derived features
        features['energy'] = self._calculate_energy(features.get('fft_bands', []))
        features['brightness'] = self._calculate_brightness(features.get('fft_bands', []))
        features['complexity'] = self._calculate_complexity(features.get('fft_bands', []))
        
        return features
    
    def _normalize_fft(self, fft_data: List[float]) -> List[float]:
        """Normalize FFT data to 0.0-1.0 range."""
        if not fft_data:
            return [0.0] * self.fft_size
        
        # Apply log scaling and normalization
        fft_array = np.array(fft_data)
        fft_array = np.log10(fft_array + 1e-10)  # Add small value to avoid log(0)
        fft_array = (fft_array - fft_array.min()) / (fft_array.max() - fft_array.min() + 1e-10)
        
        return fft_array.tolist()
    
    def _calculate_spectral_centroid(self, fft_data: List[float]) -> float:
        """Calculate spectral centroid (brightness measure)."""
        if not fft_data:
            return 0.0
        
        freqs = np.linspace(0, self.sample_rate // 2, len(fft_data))
        fft_array = np.array(fft_data)
        
        if np.sum(fft_array) == 0:
            return 0.0
        
        centroid = np.sum(freqs * fft_array) / np.sum(fft_array)
        return min(1.0, centroid / (self.sample_rate // 2))
    
    def _calculate_spectral_rolloff(self, fft_data: List[float]) -> float:
        """Calculate spectral rolloff frequency."""
        if not fft_data:
            return 0.0
        
        freqs = np.linspace(0, self.sample_rate // 2, len(fft_data))
        fft_array = np.array(fft_data)
        
        total_energy = np.sum(fft_array)
        if total_energy == 0:
            return 0.0
        
        # Find frequency where 85% of energy is below
        cumulative_energy = np.cumsum(fft_array)
        rolloff_idx = np.where(cumulative_energy >= 0.85 * total_energy)[0]
        
        if len(rolloff_idx) > 0:
            rolloff_freq = freqs[rolloff_idx[0]]
            return min(1.0, rolloff_freq / (self.sample_rate // 2))
        
        return 0.0
    
    def _smooth_envelope(self, envelope: float) -> float:
        """Apply smoothing to envelope values."""
        self.envelope_history.append(envelope)
        if len(self.envelope_history) > self.history_size:
            self.envelope_history.pop(0)
        
        return np.mean(self.envelope_history)
    
    def _smooth_peak(self, peak: float) -> float:
        """Apply smoothing to peak values."""
        self.peak_history.append(peak)
        if len(self.peak_history) > self.history_size:
            self.peak_history.pop(0)
        
        return np.mean(self.peak_history)
    
    def _calculate_energy(self, fft_bands: List[float]) -> float:
        """Calculate total energy from FFT bands."""
        if not fft_bands:
            return 0.0
        return np.mean(fft_bands)
    
    def _calculate_brightness(self, fft_bands: List[float]) -> float:
        """Calculate brightness (weighted average favoring high frequencies)."""
        if not fft_bands:
            return 0.0
        
        weights = np.linspace(0.1, 1.0, len(fft_bands))
        weighted_sum = np.sum(np.array(fft_bands) * weights)
        total_weight = np.sum(weights)
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def _calculate_complexity(self, fft_bands: List[float]) -> float:
        """Calculate spectral complexity (variance of FFT bands)."""
        if not fft_bands or len(fft_bands) < 2:
            return 0.0
        
        return np.var(fft_bands) 