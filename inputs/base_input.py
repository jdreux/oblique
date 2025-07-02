from abc import ABC, abstractmethod
from typing import Any

class BaseInput(ABC):
    """
    Abstract base class for all input sources in Oblique.
    Defines the interface for input modules.
    """
    def __init__(self, config: dict | None = None) -> None:
        """
        Initialize the input source with optional configuration.
        :param config: Optional dictionary of configuration parameters.
        """
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
        Read data from the input source.
        :return: Data from the input source (type depends on implementation).
        """
        pass 