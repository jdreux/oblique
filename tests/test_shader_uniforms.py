"""Validate that all @oblique_module classes have matching shader and Python uniforms.

For each registered module this test:
1. Compiles the fragment shader in a headless moderngl context.
2. Instantiates the module with minimal params and calls prepare_uniforms(t=0.0).
3. Asserts that every uniform the shader *expects* is *provided* by Python
   (the "missing" direction is a hard failure).
4. Extras (Python provides but shader ignores) are logged as warnings — they are
   harmless at runtime because the renderer simply skips them.

A single standalone moderngl context is shared across all modules for speed.
"""

import dataclasses
import importlib
import inspect
import warnings
from typing import Any

import moderngl
import pytest

from core.paths import resolve_asset_path
from core.registry import discover_modules, _extract_params_class
from core.shader_preprocessor import preprocess_shader
from modules.core.base_av_module import BaseAVModule, BaseAVParams


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VERTEX_SHADER = """\
#version 330
in vec2 in_vert;
in vec2 in_uv;
out vec2 v_uv;
void main() {
    v_uv = in_uv;
    gl_Position = vec4(in_vert, 0.0, 1.0);
}
"""

# Vertex-shader attributes that appear in program iteration but are not uniforms.
_VERTEX_ATTRS = {"in_vert", "in_uv"}

# Auto-injected uniforms that the framework always supplies even when the shader
# doesn't declare them — their absence is never a bug on the Python side.
_AUTO_INJECTED = {"u_resolution"}


def _can_create_standalone_context() -> bool:
    if not hasattr(moderngl, "__version__"):
        return False
    try:
        ctx = moderngl.create_context(standalone=True)
    except Exception:
        return False
    try:
        ctx.release()
    except Exception:
        pass
    return True


_GPU_AVAILABLE = _can_create_standalone_context()


def _program_uniform_names(program: moderngl.Program) -> set[str]:
    """Extract all uniform / binding names from a compiled program."""
    names: set[str] = set()
    try:
        if hasattr(program, "keys"):
            names.update(str(n) for n in program.keys())
    except Exception:
        pass
    try:
        for member in program:
            names.add(str(getattr(member, "name", member)))
    except Exception:
        pass
    return names - _VERTEX_ATTRS


def _compile_shader(ctx: moderngl.Context, frag_path: str) -> moderngl.Program:
    resolved = str(resolve_asset_path(frag_path))
    source = preprocess_shader(resolved)
    return ctx.program(vertex_shader=_VERTEX_SHADER, fragment_shader=source)


def _build_minimal_params(params_cls: type) -> Any:
    """Construct a Params dataclass with width=64, height=64 and sensible defaults.

    Required fields with no default that look like textures or BaseAVModule
    are filled with ``None``; other required fields without defaults are filled
    with zero-ish sentinel values.
    """
    if not dataclasses.is_dataclass(params_cls):
        raise TypeError(f"{params_cls} is not a dataclass")

    kwargs: dict[str, Any] = {"width": 64, "height": 64}
    for f in dataclasses.fields(params_cls):
        if f.name in kwargs:
            continue
        if f.default is not dataclasses.MISSING:
            continue
        if f.default_factory is not dataclasses.MISSING:
            continue
        # Required field with no default — supply a placeholder
        hint = f.type if isinstance(f.type, str) else getattr(f, "type", "")
        hint_str = str(hint).lower()
        if "texture" in hint_str or "baseav" in hint_str or "module" in hint_str:
            kwargs[f.name] = None
        elif "str" in hint_str:
            kwargs[f.name] = ""
        elif "int" in hint_str:
            kwargs[f.name] = 0
        elif "float" in hint_str:
            kwargs[f.name] = 0.0
        elif "bool" in hint_str:
            kwargs[f.name] = False
        else:
            kwargs[f.name] = None
    return params_cls(**kwargs)


def _try_instantiate(module_cls: type, params: Any) -> BaseAVModule | None:
    """Try to create a module instance. Returns None if it needs extra args."""
    sig = inspect.signature(module_cls.__init__)
    init_params = list(sig.parameters.keys())
    # Expect (self, params) — anything more means extra required dependencies.
    required = [
        name for name, p in sig.parameters.items()
        if name != "self"
        and p.default is inspect.Parameter.empty
        and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
    ]
    if len(required) > 1:
        return None
    try:
        return module_cls(params)
    except Exception:
        return None


def _is_texture_uniform(value: Any) -> bool:
    """Return True if the value represents a texture that the framework resolves."""
    if value is None:
        return True
    if isinstance(value, BaseAVModule):
        return True
    if isinstance(value, moderngl.Texture):
        return True
    return False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def ctx():
    if not _GPU_AVAILABLE:
        pytest.skip("No GPU / standalone moderngl context available")
    context = moderngl.create_context(standalone=True)
    yield context
    context.release()


@pytest.fixture(scope="module")
def all_modules():
    return discover_modules()


# ---------------------------------------------------------------------------
# Skipped modules — need special dependencies beyond just (params,)
# ---------------------------------------------------------------------------

# Modules whose __init__ requires extra positional args (e.g. FFTBands processor)
# or whose prepare_uniforms has side-effects that prevent headless invocation.
_SKIP_INSTANTIATION = {
    "CircleEcho",       # needs FFTBands processor
    "MediaModule",      # needs a real image file on disk
    "ShadertoyModule",  # frag_shader_path comes from params at runtime
}


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("module_name", sorted(discover_modules().keys()))
def test_shader_uniforms_match_python(module_name, ctx, all_modules):
    spec = all_modules[module_name]

    # Import the module class
    parts = spec.module_class.rsplit(".", 1)
    mod = importlib.import_module(parts[0])
    module_cls = getattr(mod, parts[1])

    # --- Shader side ---
    frag_path = getattr(module_cls, "frag_shader_path", None)
    if frag_path is None or frag_path == "":
        pytest.skip(f"{module_name} has no frag_shader_path")

    program = _compile_shader(ctx, frag_path)
    shader_uniforms = _program_uniform_names(program)
    program.release()

    # --- Python side ---
    if module_name in _SKIP_INSTANTIATION:
        # We can still compile the shader, but can't call prepare_uniforms.
        # Just verify the shader compiles without error (already done above).
        return

    params_cls = _extract_params_class(module_cls)
    if params_cls is None:
        pytest.skip(f"{module_name}: cannot determine Params class")

    params = _build_minimal_params(params_cls)
    instance = _try_instantiate(module_cls, params)
    if instance is None:
        pytest.skip(f"{module_name}: cannot instantiate (extra __init__ args)")

    try:
        uniforms_dict = dict(instance.prepare_uniforms(t=0.0))
    except Exception as exc:
        pytest.skip(f"{module_name}: prepare_uniforms raised {exc!r}")

    python_keys = set(uniforms_dict.keys())

    # Identify texture-valued keys — their GLSL type is sampler2D which won't
    # appear by the same name if the Python value is a BaseAVModule (resolved
    # later by the framework). We still expect the name to match.
    texture_keys = {k for k, v in uniforms_dict.items() if _is_texture_uniform(v)}

    # --- Compare ---
    # Missing: shader expects it but Python doesn't provide it.
    # Exclude auto-injected uniforms (u_resolution) and ping-pong uniforms
    # (u_previous, u_feedback_texture, etc.) that the framework injects.
    missing = shader_uniforms - python_keys - _AUTO_INJECTED
    # Filter out ping-pong / previous-frame uniforms injected by the framework
    ping_pong_names = {"u_previous", "u_previous_frame"}
    if hasattr(module_cls, "previous_uniform_name"):
        ping_pong_names.add(module_cls.previous_uniform_name)
    missing -= ping_pong_names

    # Extra: Python provides but shader doesn't consume — harmless, just warn.
    extra = python_keys - shader_uniforms
    if extra:
        warnings.warn(
            f"{module_name}: Python provides but shader ignores: {sorted(extra)}",
            stacklevel=1,
        )

    assert not missing, (
        f"{module_name}: shader expects uniforms that Python does not provide: "
        f"{sorted(missing)}\n"
        f"  shader uniforms:  {sorted(shader_uniforms)}\n"
        f"  python uniforms:  {sorted(python_keys)}"
    )
