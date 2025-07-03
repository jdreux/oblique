from typing import Any, TypedDict, Dict, TypeVar, Generic
from dataclasses import dataclass
from core.oblique_node import ObliqueNode

# --- Base params dataclass ---
@dataclass
class BaseAVParams:
    width: int = 800
    height: int = 600

class Uniforms(TypedDict, total=True):
    # Extend this in each module for specific uniforms
    pass

P = TypeVar('P', bound='BaseAVParams')

class BaseAVModule(ObliqueNode, Generic[P]):
    """
    Base class for all AV modules. Defines the required interface for AV modules.

    Required attributes and methods:
    - metadata: dict[str, Any] with keys 'name', 'description', 'parameters'
    - frag_shader_path: str (must be set by subclass)
    - __init__(params: BaseAVParams): Initialize the module with parameters (subclass of BaseAVParams)
    - update(params: BaseAVParams): Update the module's parameters/state
    - render(t: float) -> dict[str, Any]:
        Return a dictionary with at least:
            'frag_shader_path': str (path to the fragment shader)
            'uniforms': Uniforms (uniforms to pass to the shader)
        This data will be used by the renderer to draw the module.
    """

    metadata: dict[str, Any] = {
        "name": "BaseAVModule",
        "description": "Abstract base class for AV modules. Subclasses must define metadata, update, and render methods.",
        "parameters": {}
    }
    frag_shader_path: str  # Must be set by subclass

    def __init__(self, params: P):
        """
        Initialize the module with parameters.

        Args:
            params (BaseAVParams): Initial parameters for the module.
        """
        ObliqueNode.__init__(self)
        if not hasattr(self, 'frag_shader_path') or not isinstance(self.frag_shader_path, str):
            raise TypeError(f"{self.__class__.__name__} must define a class attribute 'frag_shader_path' (str)!")
        self.params = params

    def update(self, params: P) -> None:
        """
        Update the module's parameters/state.

        Args:
            params (BaseAVParams): Parameters to update the module's state.
        """
        self.params = params

    def render(self, t: float) -> dict[str, Any]:
        """
        Return the data needed for the renderer to render this module.

        Args:
            t (float): Current time or frame time.

        Returns:
            dict[str, Any]: Dictionary with at least 'frag_shader_path' and 'uniforms'.
        """
        raise NotImplementedError("Subclasses must implement the render() method.")
        """
        Return the data needed for the renderer to render this module.
        Should return a dict with at least 'frag_shader_path' and 'uniforms'.
        """
        raise NotImplementedError 