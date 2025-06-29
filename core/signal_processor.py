"""
Signal processor for Oblique.
Coordinates the processing layer components.
"""

from typing import Dict, Any
from processing.audio_features import AudioFeatureExtractor
from processing.signal_normalizer import SignalNormalizer
from processing.event_detector import EventDetector


class SignalProcessor:
    """Coordinate signal processing for the Oblique engine."""
    
    def __init__(self):
        """Initialize the signal processor."""
        self.audio_feature_extractor = AudioFeatureExtractor()
        self.signal_normalizer = SignalNormalizer()
        self.event_detector = EventDetector()
    
    def process_signals(self, 
                       raw_audio_data: Dict[str, Any] = None,
                       raw_midi_data: Dict[str, Any] = None,
                       raw_osc_data: Dict[str, Any] = None,
                       time_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process all input signals through the processing pipeline."""
        
        # Extract audio features
        audio_features = None
        if raw_audio_data:
            audio_features = self.audio_feature_extractor.extract_features(raw_audio_data)
        
        # Create normalized processed signals
        processed_signals = self.signal_normalizer.create_processed_signals(
            audio_features=audio_features,
            midi_data=raw_midi_data,
            osc_data=raw_osc_data,
            time_data=time_data
        )
        
        # Detect events
        events = self.event_detector.detect_events(processed_signals)
        processed_signals['events'] = events
        
        return processed_signals
    
    def get_audio_feature_extractor(self) -> AudioFeatureExtractor:
        """Get the audio feature extractor."""
        return self.audio_feature_extractor
    
    def get_signal_normalizer(self) -> SignalNormalizer:
        """Get the signal normalizer."""
        return self.signal_normalizer
    
    def get_event_detector(self) -> EventDetector:
        """Get the event detector."""
        return self.event_detector 