from abc import ABC, abstractmethod
from typing import Any
from core.oblique_node import ObliqueNode

class BaseProcessingOperator(ObliqueNode, ABC):
    """
    Abstract base class for all processing operators in Oblique.
    Defines the interface for feature extraction, normalization, and event detection modules.
    """
    def __init__(self, config: dict | None = None) -> None:
        """
        Initialize the processing operator with optional configuration.
        :param config: Optional dictionary of configuration parameters.
        """
        ObliqueNode.__init__(self)
        self.config = config or {}

    @abstractmethod
    def process(self, data: Any) -> Any:
        """
        Process input data and return the result.
        :param data: Input data (e.g., audio chunk as np.ndarray)
        :return: Processed result (type depends on implementation)
        """
        pass 