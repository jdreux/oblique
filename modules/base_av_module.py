from dataclasses import dataclass
from typing import Any, Generic, TypedDict, TypeVar

import moderngl

from core.oblique_node import ObliqueNode
from core.renderer import render_to_texture


# --- Base params dataclass ---
@dataclass
class BaseAVParams:
    width: int = 800
    height: int = 600


class Uniforms(TypedDict, total=True):
    # Extend this in each module for specific uniforms
    pass


P = TypeVar("P", bound="BaseAVParams")


class BaseAVModule(ObliqueNode, Generic[P]):
    """
    Base class for all AV modules. Defines the required interface for AV modules.

    Required attributes and methods:
    - metadata: dict[str, Any] with keys 'name', 'description', 'parameters'
    - frag_shader_path: str (must be set by subclass)
    - __init__(params: BaseAVParams): Initialize the module with parameters (subclass of BaseAVParams)
    - render_data(t: float) -> dict[str, Any]:
        Return a dictionary with at least:
            'frag_shader_path': str (path to the fragment shader)
            'uniforms': Uniforms (uniforms to pass to the shader)
        This data will be used by the renderer to draw the module.

    Optional methods:
    - render_texture(ctx: moderngl.Context, width: int, height: int, t: float) -> moderngl.Texture:
        Override this method to provide custom texture rendering behavior.
        Default implementation uses render_data() method and render_to_texture().
    """

    metadata: dict[str, Any] = {
        "name": "BaseAVModule",
        "description": "Abstract base class for AV modules. Subclasses must define metadata, update, and render methods.",
        "parameters": {},
    }
    frag_shader_path: str  # Must be set by subclass

    def __init__(self, params: P, parent: ObliqueNode | None = None):
        """
        Initialize the module with parameters.

        Args:
            params (BaseAVParams): Initial parameters for the module.
        """
        ObliqueNode.__init__(self)
        if not hasattr(self, "frag_shader_path") or not isinstance(
            self.frag_shader_path, str
        ):
            raise TypeError(
                f"{self.__class__.__name__} must define a class attribute 'frag_shader_path' (str)!"
            )
        self.params = params
        if parent:
            self.add_parent(parent)

    def render_data(self, t: float) -> dict[str, Any]:
        """
        Return the data needed for the renderer to render this module.

        Args:
            t (float): Current time or frame time.

        Returns:
            dict[str, Any]: Dictionary with at least 'frag_shader_path' and 'uniforms'.
        """
        raise NotImplementedError("Subclasses must implement the render_data() method.")

    def render_texture(
        self,
        ctx: moderngl.Context,
        width: int,
        height: int,
        t: float,
        filter=moderngl.NEAREST,
    ) -> moderngl.Texture:
        """
        Get the texture for this module. Default implementation uses render_data() method.
        Override this method to provide custom texture rendering behavior.

        Args:
            ctx (moderngl.Context): OpenGL context
            width (int): Texture width
            height (int): Texture height
            t (float): Current time in seconds

        Returns:
            moderngl.Texture: The rendered texture for this module
        """
        render_data = self.render_data(t)
        return render_to_texture(
            ctx,
            width,
            height,
            render_data["frag_shader_path"],
            render_data["uniforms"],
            filter,
        )
