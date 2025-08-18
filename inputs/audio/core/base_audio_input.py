from abc import ABC, abstractmethod
from typing import Any, List, Optional

from inputs.base_input import BaseInput


class BaseAudioInput(BaseInput, ABC):
    """Abstract base class for all audio input sources in Oblique."""

    def __init__(self, chunk_size: int) -> None:
        """Initialize the audio input source."""
        self.chunk_size = chunk_size

    @property
    @abstractmethod
    def sample_rate(self) -> int:
        """Get the sample rate of the input source in Hz."""
        ...

    @property
    @abstractmethod
    def num_channels(self) -> int:
        """Get the number of audio channels in the input source."""
        ...

    @property
    @abstractmethod
    def device_name(self) -> str:  # type: ignore[override]
        """Return a human-readable name for the input device."""
        ...

    @abstractmethod
    def start(self) -> None:
        """Start the input stream or resource."""
        ...

    @abstractmethod
    def stop(self) -> None:
        """Stop the input stream or resource."""
        ...

    @abstractmethod
    def read(self, channels=None) -> Any:
        """Read data from the input source."""
        ...

    @abstractmethod
    def peek(self, n_buffers: int = 1, channels: Optional[List[int]] = None) -> Any:
        """Return the most recent data chunk without advancing the cursor."""
        ...
