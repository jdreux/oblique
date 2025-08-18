from abc import ABC, abstractmethod
from typing import Any


class BaseInput(ABC):
    """Universal interface for all input sources.

    Concrete input classes must provide start/stop lifecycle methods and expose
    a read/peek pair for retrieving data.  Implementations may accept
    implementation specific arguments for :meth:`read` and :meth:`peek`.
    """

    @property
    @abstractmethod
    def device_name(self) -> str:
        """Return a human readable name for the input device/source."""
        raise NotImplementedError

    @abstractmethod
    def start(self) -> None:
        """Start the input stream or resource."""
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        """Stop the input stream or resource."""
        raise NotImplementedError

    @abstractmethod
    def read(self, *args, **kwargs) -> Any:
        """Return data from the input source."""
        raise NotImplementedError

    @abstractmethod
    def peek(self, *args, **kwargs) -> Any:
        """Return recent data without consuming it."""
        raise NotImplementedError
