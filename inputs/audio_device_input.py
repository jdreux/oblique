from .base_input import BaseInput
from typing import Any, Optional, List, Dict
import sounddevice as sd
import numpy as np
import collections


class AudioDeviceInput(BaseInput):
    """
    Input class that reads audio from a real-time audio device (sound card, BlackHole, etc.).
    Supports multi-channel audio and device selection.
    """
    
    def __init__(
        self, 
        device_id: Optional[int] = None,
        channels: Optional[List[int]] = None,
        samplerate: int = 44100,
        chunk_size: int = 1024,
        config: Optional[dict] = None
    ) -> None:
        """
        Initialize the audio device input.
        
        :param device_id: ID of the audio device to use. If None, uses default input device.
        :param channels: List of channel indices to capture. If None, captures all channels.
        :param samplerate: Sample rate in Hz.
        :param chunk_size: Number of samples per chunk.
        :param config: Optional configuration dictionary.
        """
        super().__init__(config)
        self.device_id = device_id
        self._channel_indices = channels
        self.samplerate = samplerate
        self.chunk_size = chunk_size
        self._stream = None
        self._last_chunk = None
        self._chunk_history = collections.deque(maxlen=4)
        
    def start(self) -> None:
        """
        Start the audio input stream.
        """
        if self._stream is not None:
            return
            
        # Get device info
        device_info = sd.query_devices(self.device_id, 'input')
        max_channels = device_info['max_input_channels']
        
        # Determine which channels to capture
        if self._channel_indices is None:
            # Capture all available channels
            channels_to_capture = list(range(max_channels))
        else:
            # Validate channel selection
            channels_to_capture = [ch for ch in self._channel_indices if ch < max_channels]
            if not channels_to_capture:
                raise ValueError(f"No valid channels selected. Device has {max_channels} channels.")
        
        self._stream = sd.InputStream(
            device=self.device_id,
            channels=len(channels_to_capture),
            samplerate=self.samplerate,
            blocksize=self.chunk_size,
            dtype=np.float32,
            callback=self._audio_callback
        )
        self._stream.start()
        
    def stop(self) -> None:
        """
        Stop the audio input stream.
        """
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._last_chunk = None
        self._chunk_history.clear()
        
    def _audio_callback(self, indata: np.ndarray, frames: int, time, status) -> None:
        """
        Callback function called by sounddevice when new audio data is available.
        """
        if status:
            print(f"Audio callback status: {status}")
        
        # Store the audio chunk
        self._last_chunk = indata.copy()
        self._chunk_history.append(indata.copy())
        
    def read(self) -> np.ndarray:
        """
        Read the next chunk of audio data.
        :return: Numpy array of shape (chunk_size, channels)
        """
        if self._stream is None:
            raise RuntimeError("AudioDeviceInput not started. Call start() first.")
        
        # Wait for the next chunk to be available
        if self._last_chunk is None:
            # If no chunk is available yet, return zeros
            num_channels = len(self._channel_indices) if self._channel_indices else 1
            return np.zeros((self.chunk_size, num_channels), dtype=np.float32)
        
        return self._last_chunk.copy()
        
    def peek(self, n_buffers: Optional[int] = None) -> Optional[np.ndarray]:
        """
        Return the most recently captured chunk or up to the last n_buffers chunks concatenated.
        :param n_buffers: Number of previous chunks to return (concatenated). If None, returns the most recent chunk.
        :return: Numpy array of shape (n*chunk_size, channels) or None if not available
        """
        if n_buffers is None:
            return self._last_chunk.copy() if self._last_chunk is not None else None
            
        if n_buffers <= 0 or len(self._chunk_history) == 0:
            return None
            
        # Get up to n_buffers most recent chunks
        chunks = list(self._chunk_history)[-n_buffers:]
        if not chunks:
            return None
        return np.concatenate(chunks, axis=0)
    
    @property
    def channels(self) -> int:
        """Get the number of channels being captured."""
        if self._stream is None:
            return len(self._channel_indices) if self._channel_indices else 1
        return self._stream.channels


def list_audio_devices() -> List[Dict[str, Any]]:
    """
    List all available audio input devices with their capabilities.
    
    :return: List of dictionaries containing device information
    """
    devices = []
    for i, device in enumerate(sd.query_devices()):
        if device['max_input_channels'] > 0:  # Only input devices
            devices.append({
                'id': i,
                'name': device['name'],
                'max_input_channels': device['max_input_channels'],
                'default_samplerate': device['default_samplerate'],
                'hostapi': device['hostapi']
            })
    return devices


def print_audio_devices() -> None:
    """
    Print a formatted list of available audio input devices with channel details.
    """
    devices = list_audio_devices()
    print("\nAvailable Audio Input Devices:")
    print("=" * 80)
    
    for device in devices:
        print(f"ID: {device['id']:2d} | {device['name']}")
        print(f"     Channels: {device['max_input_channels']:2d} | Sample Rate: {int(device['default_samplerate']):6d} Hz")
        
        # Show channel details
        if device['max_input_channels'] == 1:
            print("     Channel: 0 (Mono)")
        elif device['max_input_channels'] == 2:
            print("     Channels: 0, 1 (Stereo)")
        else:
            channels = ", ".join(str(i) for i in range(device['max_input_channels']))
            print(f"     Channels: {channels} ({device['max_input_channels']} channels)")
        
        print()


if __name__ == "__main__":
    import sys
    import time

    # Check if listing devices was requested
    if len(sys.argv) > 1 and sys.argv[1] == "--list-devices":
        print_audio_devices()
        sys.exit(0)
    
    # Test device input
    print("Testing audio device input...")
    print_audio_devices()
    
    # Use default device
    input_device = AudioDeviceInput(chunk_size=2048)
    input_device.start()
    print(f"Device Input - Samplerate: {input_device.samplerate}, Channels: {input_device.channels}")
    
    try:
        for i in range(10):
            chunk = input_device.read()
            print(f"Chunk {i}: shape={chunk.shape}, mean={chunk.mean():.4f}")
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        input_device.stop()
