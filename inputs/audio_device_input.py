import queue
import threading
from typing import Any, Dict, List, Optional, cast

import numpy as np
import sounddevice as sd

from .base_input import BaseInput


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
        chunk_size: int = 480 # 10ms at 48kHz, for real time performance.
    ) -> None:
        """
        Initialize the audio device input.

        :param device_id: ID of the audio device to use. If None, uses default input device.
        :param channels: List of channel indices to capture. If None, captures all channels.
        :param samplerate: Sample rate in Hz.
        :param chunk_size: Number of samples per chunk.
        """
        super().__init__(chunk_size=chunk_size)
        self.device_id = device_id
        self._channel_indices = channels
        self.samplerate = samplerate
        self._stream = None
        self._audio_queue = queue.Queue(maxsize=4)  # Small buffer for low latency
        self._lock = threading.Lock()  # Thread safety for audio callback
        self._running = False

    def start(self) -> None:
        """
        Start the audio input stream.
        """
        if self._stream is not None:
            return

        # Get device info
        device_info = cast(Dict[str, Any], sd.query_devices(self.device_id, "input"))
        max_channels = device_info.get("max_input_channels", 1)

        # Use device's native sample rate instead of configured one
        device_samplerate = device_info.get("default_samplerate", 44100)
        self.samplerate = int(device_samplerate)

        # Determine which channels to capture
        if self._channel_indices is None:
            # Capture all available channels
            channels_to_capture = list(range(max_channels))
        else:
            # Validate channel selection
            channels_to_capture = [ch for ch in self._channel_indices if ch < max_channels]
            if not channels_to_capture:
                raise ValueError(f"No valid channels selected. Device has {max_channels} channels.")


        # Use device's recommended blocksize for stability
        # Don't force small buffers if device doesn't support them
        device_blocksize = device_info.get("default_low_input_latency", 0.01)
        if device_blocksize > 0:
            # Convert latency to samples
            device_samples = int(device_blocksize * self.samplerate)
            self.chunk_size = max(self.chunk_size, device_samples)

        self._stream = sd.InputStream(
            device=self.device_id,
            channels=len(channels_to_capture),
            samplerate=self.samplerate,
            blocksize=self.chunk_size,
            dtype=np.float32,
            callback=self._audio_callback,
            latency="low",  # Back to low latency for correct timing
        )
        self._running = True
        self._stream.start()

    def stop(self) -> None:
        """
        Stop the audio input stream.
        """
        self._running = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        # Clear the queue
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        """
        Callback function called by sounddevice when new audio data is available.
        """
        if status:
            print(f"Audio callback status: {status}")

        if not self._running:
            return

        try:
            # Put the audio chunk in the queue, drop oldest if full
            if self._audio_queue.full():
                try:
                    self._audio_queue.get_nowait()  # Remove oldest
                except queue.Empty:
                    pass

            self._audio_queue.put_nowait(indata.copy())
        except Exception as e:
            print(f"Error in audio callback: {e}")

    def read(self) -> np.ndarray:
        """
        Read the next chunk of audio data.
        :return: Numpy array of shape (chunk_size, channels)
        """
        if self._stream is None:
            raise RuntimeError("AudioDeviceInput not started. Call start() first.")

        try:
            # Wait for the next chunk with a timeout
            chunk = self._audio_queue.get(timeout=0.1)  # 100ms timeout
            return chunk
        except queue.Empty:
            # If no chunk is available, return zeros
            num_channels = self.num_channels
            return np.zeros((self.chunk_size, num_channels), dtype=np.float32)

    def peek(self, n_buffers: Optional[int] = None) -> Optional[np.ndarray]:
        """
        Return the most recently captured chunk or up to the last n_buffers chunks concatenated.
        :param n_buffers: Number of previous chunks to return (concatenated). If None, returns the most recent chunk.
        :return: Numpy array of shape (n*chunk_size, channels) or None if not available
        """
        if n_buffers is None:
            # Return the most recent chunk if available
            try:
                # Get the most recent chunk without removing it
                chunk = self._audio_queue.get_nowait()
                # Put it back at the front
                self._audio_queue.put_nowait(chunk)
                return chunk
            except queue.Empty:
                return None

        if n_buffers <= 0:
            return None

        # For multiple buffers, we'd need to implement a different approach
        # since we can't peek at multiple items in a queue
        # For now, return the most recent chunk
        return self.peek()

    @property
    def sample_rate(self) -> int:
        """
        Get the sample rate of the input source in Hz.
        :return: Sample rate in Hz.
        """
        if self._stream is None:
            raise RuntimeError("AudioDeviceInput not started. Call start() first.")
        return self.samplerate

    @property
    def num_channels(self) -> int:
        """
        Get the number of audio channels in the input source.
        :return: Number of channels (1 for mono, 2 for stereo, etc.).
        """
        if self._stream is None:
            raise RuntimeError("AudioDeviceInput not started. Call start() first.")
        channels = self._stream.channels
        if isinstance(channels, tuple):
            return channels[0]  # Return the first element if it's a tuple
        return int(channels)

    @property
    def device_name(self) -> str:
        """
        Get a human-readable name for the input device/source.
        :return: Human-readable device name.
        """
        if self._stream is None:
            raise RuntimeError("AudioDeviceInput not started. Call start() first.")

        try:
            device_info = cast(Dict[str, Any], sd.query_devices(self.device_id, "input"))
            return device_info.get("name", f"Unknown Device {self.device_id}")
        except Exception:
            return f"Device {self.device_id}"


def get_channel_names(device_id: int) -> List[str]:
    """
    Get channel names for a specific audio device.
    This is particularly useful for devices like Elektron gear via Overbridge.

    :param device_id: ID of the audio device
    :return: List of channel names, or generic names if not available
    """
    try:
        device_info = cast(Dict[str, Any], sd.query_devices(device_id, "input"))
        max_channels = device_info.get("max_input_channels", 1)
        device_name = device_info.get("name", "Unknown Device")

        # TODO: sounddevice doesn't expose channel names, find a way to retrive channel names
        channel_names = [f"Channel {device_name} {i}" for i in range(max_channels)]

        # Ensure we don't exceed the actual number of channels
        return channel_names[:max_channels]

    except Exception:
        # Fallback to generic names
        device_info = cast(Dict[str, Any], sd.query_devices(device_id, "input"))
        max_channels = device_info.get("max_input_channels", 1)
        return [f"Channel {i}" for i in range(max_channels)]


def list_audio_devices() -> List[Dict[str, Any]]:
    """
    List all available audio input devices with their capabilities.

    :return: List of dictionaries containing device information
    """
    devices = []
    all_devices = sd.query_devices()
    for i, device in enumerate(all_devices):
        device_dict = cast(Dict[str, Any], device)
        max_channels = device_dict.get("max_input_channels", 0)
        if max_channels > 0:  # Only input devices
            channel_names = get_channel_names(i)
            devices.append(
                {
                    "id": i,
                    "name": device_dict.get("name", "Unknown Device"),
                    "max_input_channels": max_channels,
                    "default_samplerate": device_dict.get("default_samplerate", 44100),
                    "hostapi": device_dict.get("hostapi", "Unknown"),
                    "channel_names": channel_names,
                    "num_channels": len(channel_names),  # Actual number of channels with names
                }
            )
    return devices


def print_audio_devices() -> None:
    """
    Print a detailed table of available audio input devices with channel details.
    """
    devices = list_audio_devices()

    if not devices:
        print("No audio input devices found.")
        return

    print("\n" + "=" * 100)
    print("AUDIO INPUT DEVICES - CHANNEL INFORMATION")
    print("=" * 100)

    for device in devices:
        print(f"\nDevice ID: {device['id']}")
        print(f"Name: {device['name']}")
        print(f"Sample Rate: {int(device['default_samplerate'])} Hz")
        print(f"Host API: {device['hostapi']}")
        print(f"Total Channels: {device['num_channels']}")
        print("-" * 80)

        # Create channel table
        print("Channel Table:")
        print(f"{'Index':<6} {'Name':<20} {'Type':<15}")
        print("-" * 80)

        for i, channel_name in enumerate(device["channel_names"]):
            # Determine channel type based on actual channel configuration
            num_channels = device["num_channels"]
            if num_channels == 1:
                channel_type = "Mono"
            elif num_channels == 2:
                channel_type = "Stereo" if i < 2 else "N/A"
            else:
                # For multi-channel devices like Elektron gear
                if i < num_channels - 2:
                    channel_type = "Individual"
                else:
                    channel_type = "Mix"

            print(f"{i:<6} {channel_name:<20} {channel_type:<15}")

        print()


if __name__ == "__main__":
    import sys
    import time

    # Check if listing devices was requested
    if len(sys.argv) > 1:
        if sys.argv[1] == "--list-devices":
            print_audio_devices()
            sys.exit(0)

    # Test device input
    print("Testing audio device input...")
    print_audio_devices()

    # Use default device
    input_device = AudioDeviceInput(chunk_size=2048)
    input_device.start()
    print(f"Device Input - Samplerate: {input_device.samplerate}, Channels: {input_device.num_channels}")

    try:
        for i in range(10):
            chunk = input_device.read()
            print(f"Chunk {i}: shape={chunk.shape}, mean={chunk.mean():.4f}")
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        input_device.stop()
