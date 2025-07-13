import queue
import threading
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

import numpy as np
import sounddevice as sd

from core.logger import debug, error, info

from .base_input import BaseInput

if TYPE_CHECKING:
    from .audio_device_channel_input import AudioDeviceChannelInput


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
        chunk_size: int = 1024,  # 10ms at 48kHz, for real time performance.
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
        self._max_channels = 0  # Will be set in start() method

    def start(self) -> None:
        """
        Start the audio input stream.
        """
        if self._stream is not None:
            return

        # Get device info
        device_info = cast(Dict[str, Any], sd.query_devices(self.device_id, "input"))
        self._max_channels = device_info.get("max_input_channels", 1)

        # Use device's native sample rate instead of configured one
        device_samplerate = device_info.get("default_samplerate", 44100)
        self.samplerate = int(device_samplerate)

        # Validate channel selection if provided
        if self._channel_indices is not None:
            valid_channels = [ch for ch in self._channel_indices if ch < self._max_channels]
            if not valid_channels:
                # Provide more helpful error message
                requested_channels = self._channel_indices
                device_name = device_info.get("name", "Unknown Device")
                raise ValueError(
                    f"No valid channels selected. Device {device_name} has {self._max_channels} channels "
                    f"(0-{self._max_channels - 1}), but requested channels {requested_channels}."
                )

        # Use device's recommended blocksize for stability
        # Don't force small buffers if device doesn't support them
        device_blocksize = device_info.get("default_low_input_latency", 0.01)
        if device_blocksize > 0:
            # Convert latency to samples
            device_samples = int(device_blocksize * self.samplerate)
            self.chunk_size = max(self.chunk_size, device_samples)

        # Always request all channels from the device, filtering will be done in read/peek
        self._stream = sd.InputStream(
            device=self.device_id,
            channels=self._max_channels,  # Request all channels from device
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
            debug(f"Audio callback status: {status}")

        if not self._running:
            return

        try:
            # Store all channels in the queue, filtering will be done in read/peek methods
            # Put the audio chunk in the queue, drop oldest if full
            if self._audio_queue.full():
                try:
                    self._audio_queue.get_nowait()  # Remove oldest
                except queue.Empty:
                    pass

            self._audio_queue.put_nowait(indata.copy())
        except Exception as e:
            error(f"Error in audio callback: {e}")

    def _filter_channels(self, data: np.ndarray, channels: Optional[List[int]] = None) -> np.ndarray:
        """
        Filter audio data to specific channels.

        :param data: Audio data of shape (frames, all_channels)
        :param channels: List of channel indices to keep. If None, uses the default channel selection.
        :return: Filtered audio data of shape (frames, selected_channels)
        """
        if channels is not None:
            # Use provided channel selection
            selected_channels = channels
        elif self._channel_indices is not None:
            # Use default channel selection from constructor
            selected_channels = self._channel_indices
        else:
            # Return all channels
            return np.ascontiguousarray(data, dtype=np.float32)

        # Validate channel indices
        valid_channels = [ch for ch in selected_channels if 0 <= ch < data.shape[1]]
        if not valid_channels:
            raise ValueError(
                f"No valid channels selected. Available: 0-{data.shape[1] - 1}, requested: {selected_channels}"
            )

        # Return a contiguous copy to avoid C-contiguous issues
        return np.ascontiguousarray(data[:, valid_channels], dtype=np.float32)

    def read(self, channels: Optional[List[int]] = None) -> np.ndarray:
        """
        Read the next chunk of audio data.

        :param channels: List of channel indices to return. If None, uses the default channel selection.
        :return: Numpy array of shape (chunk_size, selected_channels)
        """
        if self._stream is None:
            raise RuntimeError("AudioDeviceInput not started. Call start() first.")

        try:
            # Wait for the next chunk with a timeout
            chunk = self._audio_queue.get(timeout=0.1)  # 100ms timeout
            filtered_chunk = self._filter_channels(chunk, channels)
            # Ensure the result is C-contiguous for sounddevice compatibility
            return np.ascontiguousarray(filtered_chunk, dtype=np.float32)
        except queue.Empty:
            # If no chunk is available, return zeros
            if channels is not None:
                num_channels = len([ch for ch in channels if 0 <= ch < self._max_channels])
            elif self._channel_indices is not None:
                num_channels = len(self._channel_indices)
            else:
                num_channels = self._max_channels
            return np.zeros((self.chunk_size, num_channels), dtype=np.float32)

    def peek(self, n_buffers: Optional[int] = None, channels: Optional[List[int]] = None) -> Optional[np.ndarray]:
        """
        Return the most recently captured chunk or up to the last n_buffers chunks concatenated.

        :param n_buffers: Number of previous chunks to return (concatenated). If None, returns the most recent chunk.
        :param channels: List of channel indices to return. If None, uses the default channel selection.
        :return: Numpy array of shape (n*chunk_size, selected_channels) or None if not available
        """
        if n_buffers is None:
            # Return the most recent chunk if available
            try:
                # Get the most recent chunk without removing it
                chunk = self._audio_queue.get_nowait()
                # Put it back at the front
                self._audio_queue.put_nowait(chunk)
                filtered_chunk = self._filter_channels(chunk, channels)
                # Ensure the result is C-contiguous
                return np.ascontiguousarray(filtered_chunk, dtype=np.float32)
            except queue.Empty:
                return None

        if n_buffers <= 0:
            return None

        # For multiple buffers, we'd need to implement a different approach
        # since we can't peek at multiple items in a queue
        # For now, return the most recent chunk
        return self.peek(channels=channels)

    def get_audio_input_for_channels(self, channels: List[int]) -> "AudioDeviceChannelInput":
        """
        Get a new AudioDeviceChannelInput instance that captures only the specified channels.
        """
        from .audio_device_channel_input import AudioDeviceChannelInput
        return AudioDeviceChannelInput(from_device=self, channels=channels)

    @property
    def is_started(self) -> bool:
        """
        Check if the audio input stream is started.
        :return: True if the stream is started, False otherwise.
        """
        return self._stream is not None

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

        # Return the number of selected channels, not the total device channels
        if self._channel_indices is not None:
            return len(self._channel_indices)
        else:
            # Return the total number of available channels
            return self._max_channels

    @property
    def device_name(self) -> str:
        """
        Get a human-readable name for the input device/source.
        :return: Human-readable device name.
        """
        
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
        info("No audio input devices found.")
        return

    info("\n" + "=" * 100)
    info("AUDIO INPUT DEVICES - CHANNEL INFORMATION")
    info("=" * 100)

    for device in devices:
        info(f"\nDevice ID: {device['id']}")
        info(f"Name: {device['name']}")
        info(f"Sample Rate: {int(device['default_samplerate'])} Hz")
        info(f"Host API: {device['hostapi']}")
        info(f"Total Channels: {device['num_channels']}")
        info("-" * 80)

        # Create channel table
        info("Channel Table:")
        info(f"{'Index':<6} {'Name':<20} {'Type':<15}")
        info("-" * 80)

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

            info(f"{i:<6} {channel_name:<20} {channel_type:<15}")

        info("")


if __name__ == "__main__":
    import sys
    import time

    # Check if listing devices was requested
    if len(sys.argv) > 1:
        if sys.argv[1] == "--list-devices":
            print_audio_devices()
            sys.exit(0)

    # Test device input
    info("Testing audio device input...")
    print_audio_devices()

    # Use default device
    input_device = AudioDeviceInput(chunk_size=2048)
    input_device.start()
    info(f"Device Input - Samplerate: {input_device.samplerate}, Channels: {input_device.num_channels}")

    try:
        for i in range(10):
            chunk = input_device.read()
            debug(f"Chunk {i}: shape={chunk.shape}, mean={chunk.mean():.4f}")
            time.sleep(0.1)
    except KeyboardInterrupt:
        info("\nStopping...")
    finally:
        input_device.stop()
