"""
Signal normalization for Oblique.
Normalizes various input types to 0.0-1.0 range for consistent processing.
"""

from typing import Dict, Any, Union, List
import numpy as np


class SignalNormalizer:
    """Normalize various input signals to 0.0-1.0 range."""
    
    def __init__(self):
        """Initialize the signal normalizer."""
        self.midi_ranges = {
            'note': (0, 127),
            'velocity': (0, 127),
            'cc': (0, 127),
            'pitch_bend': (-8192, 8191),
            'aftertouch': (0, 127)
        }
        
        self.osc_ranges = {
            'float': (-1.0, 1.0),
            'int': (-2147483648, 2147483647)
        }
    
    def normalize_audio_features(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize audio features to 0.0-1.0 range."""
        normalized = {}
        
        for key, value in features.items():
            if isinstance(value, (int, float)):
                normalized[key] = self._clamp_float(value)
            elif isinstance(value, list):
                normalized[key] = [self._clamp_float(v) for v in value]
            else:
                normalized[key] = value
        
        return normalized
    
    def normalize_midi(self, midi_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize MIDI data to 0.0-1.0 range."""
        normalized = {}
        
        for key, value in midi_data.items():
            if key in self.midi_ranges:
                min_val, max_val = self.midi_ranges[key]
                normalized[key] = self._normalize_range(value, min_val, max_val)
            else:
                normalized[key] = value
        
        return normalized
    
    def normalize_osc(self, osc_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize OSC data to 0.0-1.0 range."""
        normalized = {}
        
        for key, value in osc_data.items():
            if isinstance(value, (int, float)):
                # Assume OSC values are already in reasonable ranges
                normalized[key] = self._clamp_float(value)
            else:
                normalized[key] = value
        
        return normalized
    
    def normalize_time(self, time_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize time data for consistent use in modules."""
        normalized = {}
        
        for key, value in time_data.items():
            if key == 'time':
                # Keep absolute time as is, but provide normalized cycle time
                normalized['time'] = value
                normalized['time_cycle'] = (value % 10.0) / 10.0  # 10-second cycle
            elif key == 'delta_time':
                # Normalize delta time to reasonable range (0.0-1.0 for 0-100ms)
                normalized['delta_time'] = min(1.0, value * 10.0)
            else:
                normalized[key] = value
        
        return normalized
    
    def create_processed_signals(self, 
                               audio_features: Dict[str, Any] = None,
                               midi_data: Dict[str, Any] = None,
                               osc_data: Dict[str, Any] = None,
                               time_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a unified processed signals dictionary."""
        processed_signals = {
            'audio': {},
            'midi': {},
            'osc': {},
            'time': {},
            'combined': {}
        }
        
        # Normalize each input type
        if audio_features:
            processed_signals['audio'] = self.normalize_audio_features(audio_features)
        
        if midi_data:
            processed_signals['midi'] = self.normalize_midi(midi_data)
        
        if osc_data:
            processed_signals['osc'] = self.normalize_osc(osc_data)
        
        if time_data:
            processed_signals['time'] = self.normalize_time(time_data)
        
        # Create combined signals for easy access
        combined = {}
        combined.update(processed_signals['audio'])
        combined.update(processed_signals['midi'])
        combined.update(processed_signals['osc'])
        combined.update(processed_signals['time'])
        
        processed_signals['combined'] = combined
        
        return processed_signals
    
    def _normalize_range(self, value: Union[int, float], min_val: float, max_val: float) -> float:
        """Normalize a value from its range to 0.0-1.0."""
        if max_val == min_val:
            return 0.0
        return (value - min_val) / (max_val - min_val)
    
    def _clamp_float(self, value: float) -> float:
        """Clamp a float value to 0.0-1.0 range."""
        return max(0.0, min(1.0, float(value))) 