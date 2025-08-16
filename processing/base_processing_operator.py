from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")

class BaseProcessingOperator(ABC, Generic[T]):
    """
    Abstract base class for all processing operators in Oblique.
    Defines the interface for feature extraction, normalization, and event detection modules.
    """

    def __init__(self) -> None:
        """
        Initialize the processing operator with optional configuration.
        :param config: Optional dictionary of configuration parameters.
        """
        pass

    @abstractmethod
    def process(self) -> T:
        """
        Process input data and return the result.
        :param data: Input data (e.g., audio chunk as np.ndarray)
        :return: Processed result (type depends on implementation)
        """
        pass
