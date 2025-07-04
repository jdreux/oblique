from abc import ABC, abstractmethod
from typing import Any
from core.oblique_node import ObliqueNode

class BaseProcessingOperator(ObliqueNode, ABC):
    """
    Abstract base class for all processing operators in Oblique.
    Defines the interface for feature extraction, normalization, and event detection modules.
    """
    def __init__(self, parent: ObliqueNode | None = None) -> None:
        """
        Initialize the processing operator with optional configuration.
        :param config: Optional dictionary of configuration parameters.
        """
        ObliqueNode.__init__(self)
        if parent:
            self.add_parent(parent)

    @abstractmethod
    def process(self) -> Any:
        """
        Process input data and return the result.
        :param data: Input data (e.g., audio chunk as np.ndarray)
        :return: Processed result (type depends on implementation)
        """
        pass 