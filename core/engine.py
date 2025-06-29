"""
Main engine for Oblique AV synthesizer.
Handles the Input → Processing → Rendering → Output pipeline.
"""

import time
import moderngl
import glfw
import numpy as np
from typing import Dict, Any, Optional, List
from .base_module import BaseAVModule

# Import the new processing and output layers
from .signal_processor import SignalProcessor
from output.compositor import Compositor
from output.display import Display


class ObliqueEngine:
    """Main engine for the Oblique AV synthesizer following Input → Processing → Rendering → Output."""
    
    def __init__(self, width: int = 390, height: int = 844, title: str = "Oblique", audio_file: str = None):
        """Initialize the engine with window settings."""
        self.width = width
        self.height = height
        self.title = title
        self.running = False
        self.start_time = time.time()
        
        # Initialize the four layers
        self.display = None
        self.compositor = None
        self.signal_processor = SignalProcessor()
        
        # Audio integration
        self.audio_player = None
        if audio_file:
            try:
                from input.audio.audio_player import AudioPlayer
                self.audio_player = AudioPlayer(audio_file)
                print(f"Audio player initialized with: {audio_file}")
            except ImportError as e:
                print(f"Warning: Could not import audio player: {e}")
                self.audio_player = None
        
    def initialize(self):
        """Initialize all layers of the engine."""
        # Initialize display (Output layer)
        self.display = Display(self.width, self.height, self.title)
        self.display.initialize()
        
        # Initialize compositor (Output layer)
        self.compositor = Compositor(self.display.ctx, self.width, self.height)
        
        # Start audio playback if available
        if self.audio_player:
            self.audio_player.start_playback()
        
        print(f"Oblique engine initialized: {self.width}x{self.height}")
        print("Architecture: Input → Processing → Rendering → Output")
    
    def add_module(self, module: BaseAVModule):
        """Add a module to the rendering layer."""
        if module and self.display.ctx:
            module.setup(self.display.ctx)
            self.compositor.add_module(module)
            print(f"Added module: {module.metadata['name']}")
    
    def remove_module(self, module: BaseAVModule):
        """Remove a module from the rendering layer."""
        self.compositor.remove_module(module)
        module.cleanup()
        print(f"Removed module: {module.metadata['name']}")
    
    def get_time_data(self) -> Dict[str, Any]:
        """Get current time data for modules."""
        current_time = time.time() - self.start_time
        return {
            'time': current_time,
            'delta_time': 1.0 / 60.0,  # Simplified for now
            'frame_count': int(current_time * 60)
        }
    
    def get_raw_audio_data(self) -> Dict[str, Any]:
        """Get raw audio data from the audio player, or mock data if not available."""
        if self.audio_player:
            return self.audio_player.get_audio_data()
        else:
            # Fallback to mock data
            return {
                'fft': [0.1] * 64,  # Mock FFT data
                'env': 0.1,
                'peak': 0.1,
                'amplitude': 0.1,
                'is_playing': False,
                'position': 0.0,
                'duration': 0.0
            }
    
    def process_signals(self) -> Dict[str, Any]:
        """Process raw signals through the processing layer."""
        # Get raw input data
        raw_audio_data = self.get_raw_audio_data()
        time_data = self.get_time_data()
        
        # Process through the signal processor
        processed_signals = self.signal_processor.process_signals(
            raw_audio_data=raw_audio_data,
            time_data=time_data
        )
        
        return processed_signals
    
    def render_frame(self):
        """Render a single frame through the rendering and output layers."""
        # Process signals
        processed_signals = self.process_signals()
        time_data = self.get_time_data()
        
        # Render: Compose modules
        final_framebuffer = self.compositor.compose(processed_signals, time_data)
        
        # Output: Display result
        self.display.display_framebuffer(final_framebuffer)
    
    def run(self):
        """Main render loop."""
        self.running = True
        
        while not self.display.should_close() and self.running:
            # Handle events
            self.display.poll_events()
            
            # Render frame
            self.render_frame()
            
            # Cap frame rate
            time.sleep(1.0 / 60.0)
        
        self.cleanup()
    
    def cleanup(self):
        """Clean up all resources."""
        if self.audio_player:
            self.audio_player.cleanup()
        
        if self.compositor:
            self.compositor.cleanup()
        
        if self.display:
            self.display.cleanup()
        
        print("Oblique engine cleaned up") 