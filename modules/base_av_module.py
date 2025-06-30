from typing import Any, TypedDict, Dict

class Uniforms(TypedDict, total=True):
    # Extend this in each module for specific uniforms
    pass

class BaseAVModule:
    """
    Base class for all AV modules. Defines the required interface for AV modules.

    Required attributes and methods:
    - metadata: dict[str, Any] with keys 'name', 'description', 'parameters'
    - frag_shader_path: str (must be set by subclass)
    - __init__(props: Any = None): Initialize the module with properties
    - update(props: Any): Update the module's properties/state
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

    def __init__(self, props: Any = None):
        """
        Initialize the module with properties.

        Args:
            props (Any, optional): Initial properties for the module.
        """
        if not hasattr(self, 'frag_shader_path') or not isinstance(self.frag_shader_path, str):
            raise TypeError(f"{self.__class__.__name__} must define a class attribute 'frag_shader_path' (str)!")
        # Base class constructor does nothing; subclasses may override.
        pass

    def update(self, props: Any) -> None:
        """
        Update the module's properties/state.

        Args:
            props (Any): Properties to update the module's state.
        """
        raise NotImplementedError("Subclasses must implement the update() method.")

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