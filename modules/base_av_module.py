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
            • Any expression acceptable by `_resolve_texture_param` (e.g. a moderngl.Texture).
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
        # Ask the subclass for shader path + initial uniforms
        render_data = self.prepare_uniforms(t)
        initial_uniforms = dict(render_data["uniforms"])

        # Separate "regular" uniforms from off-screen passes
        base_uniforms: dict[str, Any] = {
            k: v for k, v in initial_uniforms.items() if not isinstance(v, OffscreenTexturePass)
        }

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
            render_data["frag_shader_path"],
            final_uniforms,
            filter,
            cache_tag="final",
        )

        internal_textures: dict[str, moderngl.Texture] = {}

        # Helper to process a pass and its dependencies (DFS)
        processed: set[str] = set()

        # Helper to find the key for a pass instance
        def find_pass_key(target: OffscreenTexturePass) -> str | None:
            """Find the key for a pass instance by linear search."""
            for key, instance in self.offscreen_passes.items():
                if instance is target:  # Use identity comparison
                    return key
            return None

        def _render_pass(pass_name: str) -> None:
            if pass_name in processed:
                return
            if pass_name not in self.offscreen_passes:
                raise ValueError(f"Unknown offscreen pass '{pass_name}' referenced in module {self.__class__.__name__}.")

            tex_pass = self.offscreen_passes[pass_name]

            # First ensure dependencies are rendered
            for dep_key, source in (tex_pass.inputs or {}).items():
                if isinstance(source, OffscreenTexturePass):
                    dep_name = find_pass_key(source)
                    if dep_name is None:
                        raise ValueError(
                            f"Input '{dep_key}' of pass '{pass_name}' references an OffscreenTexturePass not registered in offscreen_passes."
                        )
                    _render_pass(dep_name)

            # Now build uniforms for this pass
            pass_width = tex_pass.width if tex_pass.width is not None else width
            pass_height = tex_pass.height if tex_pass.height is not None else height

            uniforms = dict(base_uniforms)
            uniforms["u_resolution"] = (pass_width, pass_height)

            # Bind explicit inputs
            if tex_pass.inputs:
                for key, source in tex_pass.inputs.items():
                    uniform_name = f"u_{key}"

                    if isinstance(source, OffscreenTexturePass):
                        dep_name = find_pass_key(source)
                        if dep_name is None or dep_name not in internal_textures:
                            raise RuntimeError(
                                f"Dependency pass for input '{key}' of '{pass_name}' not yet rendered."
                            )
                        uniforms[uniform_name] = internal_textures[dep_name]
                    elif isinstance(source, BaseAVModule):
                        tex = source.render_texture(
                            ctx, pass_width, pass_height, t, filter
                        )
                        uniforms[uniform_name] = tex
                    elif isinstance(source, moderngl.Texture):
                        uniforms[uniform_name] = source
                    else:
                        # Fallback: resolve generically
                        tex = self._resolve_texture_param(
                            source, ctx, pass_width, pass_height, t, filter
                        )
                        uniforms[uniform_name] = tex

            # Render the pass and cache texture
            tex = render_to_texture(
                self,
                pass_width,
                pass_height,
                tex_pass.frag_shader_path,
                uniforms,
                filter,
                cache_tag=f"{pass_name}",
            )
            internal_textures[pass_name] = tex
            processed.add(pass_name)

        # Render all passes
        for name in self.offscreen_passes.keys():
            _render_pass(name)

        # ------------------------------------------------------------------
        # Final Image pass – let the module decide which pass textures to use.
        # We simply make them available as uniforms if not already provided.
        # ------------------------------------------------------------------

        final_uniforms = dict(render_data["uniforms"])

        
        for name, tex in internal_textures.items():
            uniform_name = f"u_{name}"
            final_uniforms.setdefault(uniform_name, tex)
 
        return render_to_texture(
            self,
            width,
            height,
            render_data["frag_shader_path"],
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
