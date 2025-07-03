from abc import ABC, abstractmethod
from typing import Any
from core.oblique_node import ObliqueNode

class BaseInput(ObliqueNode, ABC):
    """
    Abstract base class for all input sources in Oblique.
    Defines the interface for input modules.
    """
    def __init__(self, config: dict | None = None) -> None:
        """
        Initialize the input source with optional configuration.
        :param config: Optional dictionary of configuration parameters.
        """
        ObliqueNode.__init__(self)
        self.config = config or {}

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
    def read(self) -> Any:
        """
        Read data from the input source, potentially advancing the input cursor.
        :return: Data from the input source (type depends on implementation).
        """
        pass

    @abstractmethod
    def peek(self) -> Any:
        """
        Return the most recent data chunk without advancing the input cursor.
        This allows consumers (e.g., video/visual analysis) to access the latest data
        being played or processed, without interfering with the main data stream.
        """
        pass 