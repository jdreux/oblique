"""
Event detection for Oblique.
Detects beats, triggers, and other events from processed signals.
"""

import numpy as np
from typing import Dict, Any, List, Callable
import time


class EventDetector:
    """Detect events like beats, triggers, and threshold crossings."""
    
    def __init__(self):
        """Initialize the event detector."""
        self.beat_threshold = 0.3
        self.trigger_threshold = 0.5
        self.energy_history = []
        self.history_size = 20
        self.last_beat_time = 0
        self.min_beat_interval = 0.1  # Minimum time between beats (seconds)
        
        # Event callbacks
        self.event_callbacks = {
            'beat': [],
            'trigger': [],
            'threshold_cross': []
        }
    
    def detect_events(self, processed_signals: Dict[str, Any]) -> Dict[str, Any]:
        """Detect events from processed signals."""
        events = {
            'beat': False,
            'trigger': False,
            'threshold_cross': False,
            'energy_rise': False,
            'energy_fall': False,
            'peak_detected': False
        }
        
        # Get energy from combined signals
        energy = processed_signals.get('combined', {}).get('energy', 0.0)
        
        # Update energy history
        self.energy_history.append(energy)
        if len(self.energy_history) > self.history_size:
            self.energy_history.pop(0)
        
        # Detect beats
        events['beat'] = self._detect_beat(energy)
        
        # Detect triggers
        events['trigger'] = self._detect_trigger(energy)
        
        # Detect threshold crossings
        events['threshold_cross'] = self._detect_threshold_cross(energy)
        
        # Detect energy changes
        events['energy_rise'] = self._detect_energy_rise()
        events['energy_fall'] = self._detect_energy_fall()
        
        # Detect peaks
        events['peak_detected'] = self._detect_peak(energy)
        
        return events
    
    def _detect_beat(self, energy: float) -> bool:
        """Detect beat based on energy threshold and timing."""
        current_time = time.time()
        
        if energy > self.beat_threshold:
            if current_time - self.last_beat_time > self.min_beat_interval:
                self.last_beat_time = current_time
                return True
        
        return False
    
    def _detect_trigger(self, energy: float) -> bool:
        """Detect trigger based on high energy threshold."""
        return energy > self.trigger_threshold
    
    def _detect_threshold_cross(self, energy: float) -> bool:
        """Detect when energy crosses the beat threshold."""
        if len(self.energy_history) < 2:
            return False
        
        prev_energy = self.energy_history[-2]
        return (prev_energy <= self.beat_threshold and energy > self.beat_threshold) or \
               (prev_energy >= self.beat_threshold and energy < self.beat_threshold)
    
    def _detect_energy_rise(self) -> bool:
        """Detect when energy is rising."""
        if len(self.energy_history) < 3:
            return False
        
        # Check if energy has been rising for the last few frames
        recent_energy = self.energy_history[-3:]
        return all(recent_energy[i] <= recent_energy[i+1] for i in range(len(recent_energy)-1))
    
    def _detect_energy_fall(self) -> bool:
        """Detect when energy is falling."""
        if len(self.energy_history) < 3:
            return False
        
        # Check if energy has been falling for the last few frames
        recent_energy = self.energy_history[-3:]
        return all(recent_energy[i] >= recent_energy[i+1] for i in range(len(recent_energy)-1))
    
    def _detect_peak(self, energy: float) -> bool:
        """Detect peak in energy."""
        if len(self.energy_history) < 5:
            return False
        
        # Check if current energy is a local maximum
        window = self.energy_history[-5:]
        center_idx = len(window) // 2
        return all(window[i] <= window[center_idx] for i in range(len(window)) if i != center_idx)
    
    def add_event_callback(self, event_type: str, callback: Callable):
        """Add a callback for a specific event type."""
        if event_type in self.event_callbacks:
            self.event_callbacks[event_type].append(callback)
    
    def set_beat_threshold(self, threshold: float):
        """Set the beat detection threshold."""
        self.beat_threshold = max(0.0, min(1.0, threshold))
    
    def set_trigger_threshold(self, threshold: float):
        """Set the trigger detection threshold."""
        self.trigger_threshold = max(0.0, min(1.0, threshold))
    
    def set_min_beat_interval(self, interval: float):
        """Set the minimum time between beats."""
        self.min_beat_interval = max(0.01, interval) 