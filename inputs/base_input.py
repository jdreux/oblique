from abc import ABC, abstractmethod
from typing import Any

from core.oblique_node import ObliqueNode


class BaseInput(ObliqueNode, ABC):
    """
    Abstract base class for all input sources in Oblique.
    Defines the interface for input modules.
    """

    def __init__(self, chunk_size: int) -> None:
        """
        Initialize the input source with optional configuration.
        :param config: Optional dictionary of configuration parameters.
        """
        ObliqueNode.__init__(self)
        self.chunk_size = chunk_size

    @property
    @abstractmethod
    def sample_rate(self) -> int:
        """
        Get the sample rate of the input source in Hz.
        :return: Sample rate in Hz.
        """
        pass

    @property
    @abstractmethod
    def num_channels(self) -> int:
        """
        Get the number of audio channels in the input source.
        :return: Number of channels (1 for mono, 2 for stereo, etc.).
        """
        pass

    @property
    @abstractmethod
    def device_name(self) -> str:
        """
        Get a human-readable name for the input device/source.
        :return: Human-readable device name.
        """
        pass

    @abstractmethod
    def start(self) -> None:
        """
        Start the input stream or resource.
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """
        Stop the input stream or resource.
        """
        pass

    @abstractmethod
    def read(self, channels=None) -> Any:
        """
        Read data from the input source, potentially advancing the input cursor.
        :param channels: Optional channel selection (implementation specific).
        :return: Data from the input source (type depends on implementation).
        """
        pass

    @abstractmethod
    def peek(self, n_buffers=None, channels=None) -> Any:
        """
        Return the most recent data chunk without advancing the input cursor.
        This allows consumers (e.g., video/visual analysis) to access the latest data
        being played or processed, without interfering with the main data stream.
        :param n_buffers: Optional number of buffers to peek (implementation specific).
        :param channels: Optional channel selection (implementation specific).
        :return: Data from the input source (type depends on implementation).
        """
        pass
