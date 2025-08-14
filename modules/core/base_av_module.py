from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Generic, TypedDict, TypeVar, Union, cast, overload

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


# --- Unified texture pass dataclass ---
@dataclass
class TexturePass:
    """A renderable texture pass used for both on-screen and off-screen rendering.

    Attributes
    ----------
    name:
        Optional stable name for caching and debugging. If omitted, an internal id() is used.
    frag_shader_path:
        Path to the fragment shader for this pass.
    uniforms:
        Mapping uniform_name → source where source can be:
            • A `TexturePass` instance – its rendered texture will be injected.
            • A `BaseAVModule` instance – its rendered texture will be injected.
            • A `moderngl.Texture` instance.
            • Any primitive value (int, float, bool, str, tuple, list, etc.)
        At runtime each pair produces a uniform named ``u_<uniform_name>`` unless the key
        already starts with ``u_``.
    width / height:
        Optional fixed resolution for this pass. If omitted, the caller's resolution is used.
    ping_pong:
        Enable double-buffered rendering. When true, the pass alternates cached targets per frame.
    previous_uniform_name:
        If ping-pong is enabled and a previous texture exists, it will be injected under this
        uniform name (default: ``u_previous``).
    """

    frag_shader_path: str
    uniforms: dict[str, Union["TexturePass", "BaseAVModule", moderngl.Texture, int, float, bool, str, tuple, list]] = field(default_factory=dict)
    width: int | None = None
    height: int | None = None
    ping_pong: bool = False
    name: str | None = None
    previous_uniform_name: str = "u_previous"


# Backwards-compatibility alias for older modules
OffscreenTexturePass = TexturePass


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
    ping_pong: bool = False
    previous_uniform_name: str = "u_previous_frame"

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

        # Sane defaults for development: a single main pass with the module's shader
        self.texture_pass: TexturePass = TexturePass(
            frag_shader_path=self.frag_shader_path,
            uniforms={},
            ping_pong=self.ping_pong,
            previous_uniform_name=self.previous_uniform_name,
            name=f"{self.__class__.__name__}:{id(self)}",
        )

        # Internal frame counter and per-pass history for ping-pong
        self._frame_index: int = 0
        self._texture_history: dict[str, moderngl.Texture] = {}

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

        The rendering pipeline traverses any TexturePass instances
        returned by ``prepare_uniforms`` (or attached to the module as nested
        dependencies) to build a dependency graph on-the-fly.
        Each pass inherits the non-pass uniforms defined for the parent module
        and can in turn declare additional texture inputs via its own
        ``uniforms`` mapping.

        The traversal guarantees that:
        1. Each TexturePass is rendered exactly once per frame.
        2. Dependencies are rendered first (depth-first).
        3. The resulting textures are substituted back into the final uniforms
           before the main shader is rendered.
        4. When ping_pong is enabled, two cached targets are alternated and the
           previous texture is injected under ``previous_uniform_name`` if available.
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

            # Only include non-TexturePass in base_uniforms
            if not isinstance(value, TexturePass):
                base_uniforms[key] = value

        # Per-call caches/state
        processed: dict[str, moderngl.Texture] = {}
        owner_tag = f"{self.__class__.__name__}:{self.id}"

        # Render every TexturePass referenced in the initial uniforms to get final uniforms
        final_uniforms = dict(base_uniforms)
        for uniform_name, value in initial_uniforms.items():
            if isinstance(value, TexturePass):
                final_uniforms[uniform_name] = self._render_texture_pass(
                    pass_obj=value,
                    ctx=ctx,
                    parent_width=width,
                    parent_height=height,
                    t=t,
                    texture_filter=filter,
                    inherited_uniforms=final_uniforms,
                    processed=processed,
                    owner_tag=owner_tag,
                )
            else:
                final_uniforms[uniform_name] = value

        # Ensure the main/root pass gets its own resolution
        final_uniforms.setdefault("u_resolution", (width, height))

        # Render the root/main pass (self.texture_pass) with inherited uniforms
        root_tex = self._render_texture_pass(
            pass_obj=self.texture_pass,
            ctx=ctx,
            parent_width=width,
            parent_height=height,
            t=t,
            texture_filter=filter,
            inherited_uniforms=final_uniforms,
            processed=processed,
            owner_tag=owner_tag,
        )

        # Advance frame index after completing the full render of this module
        self._frame_index += 1

        return root_tex

    def _render_texture_pass(
        self,
        pass_obj: TexturePass,
        ctx: moderngl.Context,
        parent_width: int,
        parent_height: int,
        t: float,
        texture_filter: int,
        inherited_uniforms: dict[str, Any],
        processed: dict[str, moderngl.Texture],
        owner_tag: str,
    ) -> moderngl.Texture:
        """Render a single TexturePass, resolving dependencies depth-first.

        This method is side-effect free except for updating the provided `processed`
        cache and the module's internal ping-pong history.
        """
        # Memoisation within a frame
        memo_key = f"{id(pass_obj)}:{parent_width}x{parent_height}"
        if memo_key in processed:
            return processed[memo_key]

        pass_width = pass_obj.width if pass_obj.width is not None else parent_width
        pass_height = pass_obj.height if pass_obj.height is not None else parent_height

        # Build uniforms for this pass starting from inherited uniforms
        uniforms: dict[str, Any] = dict(inherited_uniforms)
        uniforms["u_resolution"] = (pass_width, pass_height)

        # Resolve explicit texture inputs / dependencies declared on the pass
        for key, source in (pass_obj.uniforms or {}).items():
            uniform_name = key if key.startswith("u_") else f"u_{key}"

            if isinstance(source, TexturePass):
                tex = self._render_texture_pass(
                    pass_obj=source,
                    ctx=ctx,
                    parent_width=pass_width,
                    parent_height=pass_height,
                    t=t,
                    texture_filter=texture_filter,
                    inherited_uniforms=uniforms,
                    processed=processed,
                    owner_tag=owner_tag,
                )
            elif isinstance(source, BaseAVModule):
                tex = source.render_texture(ctx, pass_width, pass_height, t, texture_filter)
            elif isinstance(source, moderngl.Texture):
                tex = source
            else:
                # Primitive uniforms are passed as-is
                tex = source

            uniforms[uniform_name] = tex

        # If ping-pong is enabled, inject previous texture if available (or create a zero texture on first frame)
        pass_tag = pass_obj.name or str(id(pass_obj))
        cache_tag = pass_tag
        if pass_obj.ping_pong:
            parity = self._frame_index % 2
            prev_parity = 1 - parity
            cache_tag = f"{pass_tag}:pp:{parity}"
            prev_key = f"{owner_tag}:{pass_tag}:pp:{prev_parity}:{pass_width}x{pass_height}"
            prev_tex = self._texture_history.get(prev_key)
            if prev_tex is None:
                # Sane default: provide a zero-initialized texture as previous
                prev_tex = ctx.texture((pass_width, pass_height), 4, dtype="f4", alignment=1)
                prev_tex.filter = (texture_filter, texture_filter)
                prev_tex.repeat_x = False
                prev_tex.repeat_y = False
            prev_uniform = pass_obj.previous_uniform_name or "u_previous"
            uniforms[prev_uniform] = prev_tex

        # Render the pass itself
        tex = render_to_texture(
            self,
            pass_width,
            pass_height,
            pass_obj.frag_shader_path,
            cast(Uniforms, uniforms),
            texture_filter,
            cache_tag=cache_tag,
        )

        # Update memo and ping-pong history
        processed[memo_key] = tex
        if pass_obj.ping_pong:
            current_key = f"{owner_tag}:{pass_tag}:pp:{self._frame_index % 2}:{pass_width}x{pass_height}"
            self._texture_history[current_key] = tex

        return tex

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
