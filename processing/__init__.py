"""
Signal processing layer for Oblique.
Handles feature extraction, normalization, and event detection.
"""

from .audio_features import AudioFeatureExtractor
from .signal_normalizer import SignalNormalizer
from .event_detector import EventDetector

__all__ = ['AudioFeatureExtractor', 'SignalNormalizer', 'EventDetector'] 