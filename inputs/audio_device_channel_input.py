from typing import TYPE_CHECKING, List, Optional

import numpy as np

from .base_input import BaseInput

if TYPE_CHECKING:
    from .audio_device_input import AudioDeviceInput


class AudioDeviceChannelInput(BaseInput):
    """
    Input class that wraps a parent AudioDeviceInput and filters for specific channels.
    This allows creating multiple channel-specific inputs from a single audio device.
    Useful for routing different channels to different modules or processing chains.
    """

    def __init__(
        self,
        from_device: "AudioDeviceInput",
        channels: List[int],
    ) -> None:
        """
        Initialize the channel-specific audio input.

        :param from_device: The parent AudioDeviceInput to delegate to
        :param channels: List of channel indices to capture from the parent
        :param chunk_size: Override chunk size. If None, uses parent's chunk size
        """
        # Use parent's chunk size if not specified
        chunk_size = from_device.chunk_size

        super().__init__(chunk_size=chunk_size)

        self.from_device = from_device
        self.channels = channels

        # # Validate that parent is started
        # if not hasattr(parent_input, '_stream') or parent_input._stream is None:
        #     raise RuntimeError("Parent AudioDeviceInput must be started before creating AudioDeviceChannelInput")

    def start(self) -> None:
        """
        Start the channel input. This is a no-op since we delegate to parent.
        The parent should already be started.
        """
        if not self.from_device.is_started:
            self.from_device.start()

    def stop(self) -> None:
        """
        Stop the channel input. This is a no-op since we delegate to parent.
        The parent manages its own lifecycle.
        """
        # We don't stop the parent since other channel inputs might be using it
        self.from_device.stop()

    def read(self, channels: Optional[List[int]] = None) -> np.ndarray:
        """
        Read the next chunk of audio data for the specified channels.

        :param channels: List of channel indices relative to this input's channel selection.
                       If None, returns all channels configured for this input.
        :return: Numpy array of shape (chunk_size, selected_channels)
        """
        # Get all channels from parent
        return self.from_device.read(channels=self.channels )

        # # Filter to our configured channels
        # if channels is not None:
        #     # Map relative channel indices to absolute parent channel indices
        #     absolute_channels = [self.channels[i] for i in channels if i < len(self.channels)]
        #     if not absolute_channels:
        #         raise ValueError(f"No valid channels selected. Available: 0-{len(self.channels)-1}, requested: {channels}")

        #     # Get the filtered data from parent
        #     filtered_data = self.parent_input._filter_channels(parent_data, absolute_channels)
        # else:
        #     # Use our configured channels
        #     filtered_data = self.parent_input._filter_channels(parent_data, self.channels)

        # return filtered_data

    def peek(self, n_buffers: Optional[int] = None, channels: Optional[List[int]] = None) -> Optional[np.ndarray]:
        """
        Return the most recently captured chunk or up to the last n_buffers chunks concatenated.

        :param n_buffers: Number of previous chunks to return (concatenated). If None, returns the most recent chunk.
        :param channels: List of channel indices relative to this input's channel selection.
                       If None, returns all channels configured for this input.
        :return: Numpy array of shape (n*chunk_size, selected_channels) or None if not available
        """
        # Get all channels from parent
        return self.from_device.peek(n_buffers, channels=self.channels)

        # if parent_data is None:
        #     return None

        # Filter to our configured channels
        # if channels is not None:
        #     # Map relative channel indices to absolute parent channel indices
        #     absolute_channels = [self.channels[i] for i in channels if i < len(self.channels)]
        #     if not absolute_channels:
        #         raise ValueError(f"No valid channels selected. Available: 0-{len(self.channels)-1}, requested: {channels}")

        #     # Get the filtered data from parent
        #     filtered_data = self.parent_input._filter_channels(parent_data, absolute_channels)
        # else:
        #     # Use our configured channels
        #     filtered_data = self.parent_input._filter_channels(parent_data, self.channels)

        # return filtered_data

    @property
    def sample_rate(self) -> int:
        """
        Get the sample rate of the input source in Hz.
        :return: Sample rate in Hz.
        """
        return self.from_device.sample_rate

    @property
    def num_channels(self) -> int:
        """
        Get the number of audio channels in this channel-specific input.
        :return: Number of channels configured for this input.
        """
        return len(self.channels)

    @property
    def device_name(self) -> str:
        """
        Get a human-readable name for the input device/source.
        :return: Human-readable device name with channel information.
        """
        parent_name = self.from_device.device_name
        channel_str = ", ".join(str(ch) for ch in self.channels)
        return f"{parent_name} (channels: {channel_str})"

    @property
    def selected_channels(self) -> List[int]:
        """
        Get the list of channel indices this input is configured to capture.
        :return: List of channel indices.
        """
        return self.channels.copy()
