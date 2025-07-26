from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Generic, TypedDict, TypeVar, Union, overload

import moderngl

from core.oblique_node import ObliqueNode
from core.renderer import render_to_texture
from processing.base_processing_operator import BaseProcessingOperator

# Dynamic parameter types - can be static values or computed at runtime
ParamInt = Union[int, Callable[[], int], BaseProcessingOperator[int]]
ParamFloat = Union[float, Callable[[], float], BaseProcessingOperator[float]]
ParamBool = Union[bool, Callable[[], bool], BaseProcessingOperator[bool]]
ParamStr = Union[str, Callable[[], str], BaseProcessingOperator[str]]

# List versions for array parameters
ParamIntList = Union[list[int], Callable[[], list[int]], BaseProcessingOperator[list[int]]]
ParamFloatList = Union[list[float], Callable[[], list[float]], BaseProcessingOperator[list[float]]]
ParamBoolList = Union[list[bool], Callable[[], list[bool]], BaseProcessingOperator[list[bool]]]
ParamStrList = Union[list[str], Callable[[], list[str]], BaseProcessingOperator[list[str]]]

# Texture params
ParamTexture = Union[moderngl.Texture, Callable[[], moderngl.Texture], "BaseAVModule"]
ParamTextureList = Union[list[moderngl.Texture], Callable[[], list[moderngl.Texture]], list["BaseAVModule"]]

# --- Base params dataclass ---
@dataclass
class BaseAVParams:
    width: ParamInt
    height: ParamInt


class Uniforms(TypedDict, total=True):
    # Extend this in each module for specific uniforms
    u_resolution: tuple[int, int]


P = TypeVar("P", bound="BaseAVParams")


class RenderData(TypedDict):
    frag_shader_path: str
    uniforms: Uniforms


class BaseAVModule(ObliqueNode, ABC, Generic[P]):
    """
    Base class for all AV modules. Defines the required interface for AV modules.

    Required attributes and methods:
    - metadata: dict[str, Any] with keys 'name', 'description', 'parameters'
    - frag_shader_path: str (must be set by subclass)
    - __init__(params: BaseAVParams): Initialize the module with parameters (subclass of BaseAVParams)
    - prepare_uniforms(t: float) -> RenderData:
        Prepare uniform data and shader information for rendering. Return a RenderData dict with:
            'frag_shader_path': str (path to the fragment shader)
            'uniforms': Uniforms (uniforms to pass to the shader)
        This data will be used by the renderer to draw the module.

    Optional methods:
    - render_texture(ctx: moderngl.Context, width: int, height: int, t: float) -> moderngl.Texture:
        Override this method to provide custom texture rendering behavior.
        Default implementation uses prepare_uniforms() method and render_to_texture().
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

    @abstractmethod
    def prepare_uniforms(self, t: float) -> RenderData:
        """
        Prepare the uniform data and shader information needed for rendering.
        
        This method is called by render_texture() to compute the current state
        of uniforms (shader parameters) and return the shader path. The returned
        data is used by the renderer to draw the module.
        
        Args:
            t (float): Current time in seconds, used for animation and time-based effects.

        Returns:
            RenderData: Dictionary containing:
                - 'frag_shader_path': str - Path to the fragment shader file
                - 'uniforms': Uniforms - TypedDict of uniform values to pass to the shader
                
        Note:
            This method should be stateless and deterministic for the same input time.
            All time-varying effects should be computed here based on the time parameter.
        """

    def render_texture(
        self,
        ctx: moderngl.Context,
        width: int,
        height: int,
        t: float,
        filter=moderngl.NEAREST,
    ) -> moderngl.Texture:
        """
        Get the texture for this module. Default implementation uses prepare_uniforms() method.
        Override this method to provide custom texture rendering behavior.

        Args:
            ctx (moderngl.Context): OpenGL context
            width (int): Texture width
            height (int): Texture height
            t (float): Current time in seconds

        Returns:
            moderngl.Texture: The rendered texture for this module
        """
        render_data = self.prepare_uniforms(t)
        # Uniforms is a TypedDict, but render_to_texture expects dict[str, Any].
        # This cast is safe because TypedDict is a dict at runtime.
        return render_to_texture(
            self,
            width,
            height,
            render_data["frag_shader_path"],
            render_data["uniforms"],
            filter,
        )

    @overload
    def _resolve_param(self, param: ParamInt) -> int: ...

    @overload
    def _resolve_param(self, param: ParamFloat) -> float: ...

    @overload
    def _resolve_param(self, param: ParamBool) -> bool: ...

    @overload
    def _resolve_param(self, param: ParamStr) -> str: ...

    @overload
    def _resolve_param(self, param: ParamIntList) -> list[int]: ...

    @overload
    def _resolve_param(self, param: ParamFloatList) -> list[float]: ...

    @overload
    def _resolve_param(self, param: ParamBoolList) -> list[bool]: ...

    @overload
    def _resolve_param(self, param: ParamStrList) -> list[str]: ...

    def _resolve_param(self, param: ParamInt | ParamFloat | ParamBool | ParamStr | ParamIntList | ParamFloatList |
        ParamBoolList | ParamStrList) -> int | float | bool | str | list[int] | list[float] | list[bool] | list[str]:
        if isinstance(param, Callable):
            return param()
        elif isinstance(param, BaseProcessingOperator):
            return param.process()
        else:
            return param

    @overload
    def _resolve_texture_param(self, param: ParamTexture, ctx: moderngl.Context, width: int,
        height: int, t: float, filter: int) -> moderngl.Texture: ...

    @overload
    def _resolve_texture_param(self, param: ParamTextureList, ctx: moderngl.Context, width: int,
        height: int, t: float, filter: int) -> list[moderngl.Texture]: ...

    def _resolve_texture_param(self, param: ParamTexture | ParamTextureList, ctx: moderngl.Context, width: int,
        height: int, t: float, filter: int) -> moderngl.Texture | list[moderngl.Texture]:
        if isinstance(param, Callable):
            return param()
        elif isinstance(param, BaseAVModule):
            return param.render_texture(ctx, width, height, t, filter)
        elif isinstance(param, list):
            return [self._resolve_texture_param(p, ctx, width, height, t, filter) for p in param]
        else:
            return param

    def _resolve_resolution(self) -> tuple[int, int]:
        """ Helper method to resolve the resolution of the module. """
        return (self._resolve_param(self.params.width), self._resolve_param(self.params.height))
