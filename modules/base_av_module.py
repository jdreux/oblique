from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from core.logger import debug
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


# --- Off-screen texture pass dataclass ---
@dataclass
class OffscreenTexturePass:
    """An internal off-screen render step.

    Attributes
    ----------
    frag_shader_path:
        Path to the fragment shader for this pass.
    inputs:
        Mapping *uniform_name → source* where *source* can be:
            • A `OffscreenTexturePass` instance – its rendered texture will be injected.
            • A `BaseAVModule` instance – its rendered texture will be injected.
            • A `moderngl.Texture` instance.
        At runtime each pair produces a uniform named ``u_<uniform_name>`` bound to the
        resulting texture.
    width / height:
        Optional fixed resolution for this pass.  If omitted the  module's requested
        resolution is used.
    ping_pong:
        Placeholder for future double-buffering support.
    """

    frag_shader_path: str
    offscreen_inputs: dict[str, Union["OffscreenTexturePass", "BaseAVModule", moderngl.Texture]] = field(default_factory=dict)
    width: int | None = None
    height: int | None = None
    ping_pong: bool = False


class Uniforms(TypedDict, total=True):
    # Extend this in each module for specific uniforms
    u_resolution: tuple[int, int]


P = TypeVar("P", bound="BaseAVParams")
U = TypeVar("U", bound="Uniforms")


class BaseAVModule(ObliqueNode, ABC, Generic[P, U]):
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
    def prepare_uniforms(self, t: float) -> U:
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
        Render this module and return a texture.

        The rendering pipeline traverses any OffscreenTexturePass instances
        returned by ``prepare_uniforms`` to build a dependency graph on-the-fly.
        Each pass inherits the *non-pass* uniforms defined for the parent module
        and can in turn declare additional texture inputs via the
        ``offscreen_inputs`` mapping.

        The traversal guarantees that:
        1. Each OffscreenTexturePass is rendered exactly once.
        2. Dependencies are rendered first (depth-first).
        3. The resulting textures are substituted back into the final uniforms
           before the main shader is rendered.
        """
        # Ask the subclass for initial uniforms
        initial_uniforms = dict(self.prepare_uniforms(t))

        # Resolve BaseAVModule (or list thereof) to textures and separate base uniforms in a single loop
        base_uniforms: dict[str, Any] = {}
        for key, value in list(initial_uniforms.items()):
            # Resolve BaseAVModule or list[BaseAVModule] to texture(s)
            if isinstance(value, BaseAVModule) or (isinstance(value, list) and all(isinstance(v, BaseAVModule) for v in value)):
                value = self._resolve_texture_param(value, ctx, width, height, t, filter)
                initial_uniforms[key] = value  # update in-place for later use

            # Only include non-OffscreenTexturePass in base_uniforms
            if not isinstance(value, OffscreenTexturePass):
                base_uniforms[key] = value

        processed: dict[int, moderngl.Texture] = {}

        def _render_pass(pass_obj: OffscreenTexturePass) -> moderngl.Texture:
            # Memoisation
            key = id(pass_obj)
            if key in processed:
                return processed[key]

            pass_width = pass_obj.width if pass_obj.width is not None else width
            pass_height = pass_obj.height if pass_obj.height is not None else height

            # Build uniforms for this pass starting from parent's non-pass uniforms
            uniforms = dict(base_uniforms)
            uniforms["u_resolution"] = (pass_width, pass_height)

            # Resolve explicit texture inputs / dependencies
            for key, source in (pass_obj.offscreen_inputs or {}).items():
                uniform_name = key if key.startswith("u_") else f"u_{key}"

                if isinstance(source, OffscreenTexturePass):
                    tex = _render_pass(source)
                elif isinstance(source, BaseAVModule):
                    tex = source.render_texture(ctx, pass_width, pass_height, t, filter)
                else:
                    assert(isinstance(source, moderngl.Texture), f"Invalid texture source: {source} of type {type(source)}")
                    tex = source

                uniforms[uniform_name] = tex

            # Finally render the pass itself
            tex = render_to_texture(
                self,
                pass_width,
                pass_height,
                pass_obj.frag_shader_path,
                uniforms,
                filter,
                cache_tag=str(id(pass_obj)),
            )
            processed[key] = tex
            return tex

        # Render every OffscreenTexturePass referenced in the initial uniforms
        final_uniforms = dict(base_uniforms)  # start with regular uniforms
        for uniform_name, value in initial_uniforms.items():
            if isinstance(value, OffscreenTexturePass):
                final_uniforms[uniform_name] = _render_pass(value)
            else:
                final_uniforms[uniform_name] = value

        # Ensure the main pass gets its own resolution
        final_uniforms.setdefault("u_resolution", (width, height))

        return render_to_texture(
            self,
            width,
            height,
            self.frag_shader_path,
            final_uniforms,
            filter,
            cache_tag="final",
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
