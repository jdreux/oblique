"""
Audio Player Module for Oblique
Handles audio file loading and real-time playback with amplitude analysis.
"""

import numpy as np
import soundfile as sf
import sounddevice as sd
import threading
import time
from typing import Dict, Any, Optional, List
import queue


class AudioPlayer:
    """Real-time audio player with amplitude analysis and playback."""
    
    def __init__(self, audio_file: str = None):
        """Initialize the audio player."""
        self.audio_file = audio_file
        self.audio_data = None
        self.sample_rate = 44100
        self.channels = 1
        self.current_position = 0
        self.is_playing = False
        self.loop = True
        
        # Audio analysis buffers
        self.fft_size = 64
        self.fft_buffer = np.zeros(self.fft_size)
        self.amp_buffer = np.zeros(1024)  # For envelope following
        
        # Threading for real-time playback
        self.playback_thread = None
        self.audio_queue = queue.Queue()
        self.stream = None
        
        # Analysis results
        self.current_amplitude = 0.0
        self.current_fft = np.zeros(self.fft_size)
        self.current_envelope = 0.0
        self.current_peak = 0.0
        
        if audio_file:
            self.load_audio(audio_file)
    
    def load_audio(self, audio_file: str):
        """Load an audio file for playback."""
        try:
            print(f"Loading audio file: {audio_file}")
            self.audio_data, self.sample_rate = sf.read(audio_file)
            
            # Convert to mono if stereo
            if len(self.audio_data.shape) > 1:
                self.audio_data = np.mean(self.audio_data, axis=1)
            
            self.channels = 1
            self.current_position = 0
            print(f"Loaded audio: {len(self.audio_data)} samples at {self.sample_rate}Hz")
            
        except Exception as e:
            print(f"Error loading audio file: {e}")
            self.audio_data = None
    
    def start_playback(self):
        """Start audio playback in a separate thread and play through speakers."""
        if self.audio_data is None:
            print("No audio file loaded")
            return
        
        if self.is_playing:
            return
        
        self.is_playing = True
        self.playback_thread = threading.Thread(target=self._playback_loop)
        self.playback_thread.daemon = True
        self.playback_thread.start()
        print("Audio playback started")
    
    def stop_playback(self):
        """Stop audio playback."""
        self.is_playing = False
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        if self.playback_thread:
            self.playback_thread.join(timeout=1.0)
        print("Audio playback stopped")
    
    def _playback_loop(self):
        """Main playback loop running in separate thread. Streams audio and analyzes it."""
        frame_size = 1024
        sample_delay = frame_size / self.sample_rate
        
        def callback(outdata, frames, time_info, status):
            if not self.is_playing or self.audio_data is None:
                outdata[:] = np.zeros((frames, 1), dtype=np.float32)
                return
            end_pos = min(self.current_position + frames, len(self.audio_data))
            chunk = self.audio_data[self.current_position:end_pos]
            if len(chunk) < frames:
                if self.loop:
                    # Loop to start
                    remain = frames - len(chunk)
                    chunk = np.concatenate((chunk, self.audio_data[:remain]))
                    self.current_position = remain
                else:
                    chunk = np.pad(chunk, (0, frames - len(chunk)))
                    self.is_playing = False
                    self.current_position = 0
            else:
                self.current_position += frames
            outdata[:, 0] = chunk.astype(np.float32)
            # Analyze this chunk
            self._analyze_frame(chunk)
        
        # Open output stream
        with sd.OutputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype='float32',
            callback=callback,
            blocksize=frame_size,
            finished_callback=None
        ) as self.stream:
            while self.is_playing:
                time.sleep(0.05)
    
    def _analyze_frame(self, frame: np.ndarray):
        """Analyze an audio frame for amplitude and FFT data."""
        # Update amplitude buffer
        self.amp_buffer = np.roll(self.amp_buffer, -len(frame))
        self.amp_buffer[-len(frame):] = np.abs(frame)
        
        # Calculate current amplitude (RMS)
        self.current_amplitude = np.sqrt(np.mean(frame**2))
        
        # Calculate envelope (smoothed amplitude)
        self.current_envelope = np.mean(self.amp_buffer)
        
        # Calculate peak
        self.current_peak = np.max(self.amp_buffer)
        
        # Calculate FFT
        if len(frame) >= self.fft_size:
            fft_data = np.fft.fft(frame[:self.fft_size])
            # Get magnitude spectrum (first half)
            magnitude = np.abs(fft_data[:self.fft_size//2])
            # Normalize and scale
            self.current_fft = magnitude / np.max(magnitude) if np.max(magnitude) > 0 else np.zeros(self.fft_size//2)
            # Pad to full FFT size if needed
            if len(self.current_fft) < self.fft_size:
                self.current_fft = np.pad(self.current_fft, (0, self.fft_size - len(self.current_fft)))
    
    def get_audio_data(self) -> Dict[str, Any]:
        """Get current audio analysis data."""
        return {
            'fft': self.current_fft.tolist(),
            'env': float(self.current_envelope),
            'peak': float(self.current_peak),
            'amplitude': float(self.current_amplitude),
            'is_playing': self.is_playing,
            'position': self.current_position / self.sample_rate if self.audio_data is not None else 0.0,
            'duration': len(self.audio_data) / self.sample_rate if self.audio_data is not None else 0.0
        }
    
    def set_loop(self, loop: bool):
        """Set whether audio should loop."""
        self.loop = loop
    
    def seek(self, position: float):
        """Seek to a specific position in the audio (in seconds)."""
        if self.audio_data is not None:
            sample_pos = int(position * self.sample_rate)
            self.current_position = max(0, min(sample_pos, len(self.audio_data)))
    
    def cleanup(self):
        """Clean up resources."""
        self.stop_playback() 