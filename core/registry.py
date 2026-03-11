"""Module registry for AI-friendly discovery and introspection.

The registry is populated via the ``@oblique_module`` decorator and can be
rebuilt by discovering and importing modules under the ``modules`` package.
"""

from __future__ import annotations

from dataclasses import MISSING, asdict, dataclass, fields, is_dataclass
from enum import Enum
import importlib
import inspect
import pkgutil
from pathlib import Path
from typing import Any, Callable, Sequence, get_args, get_origin


_SKIP_PARAMS = {"width", "height"}
_REGISTRY_CONFIG_ATTR = "__oblique_registry_config__"


@dataclass
class ParamSpec:
    """Normalized parameter metadata exposed by the module registry."""

    name: str
    type: str
    default: Any
    min: float | None
    max: float | None
    description: str
    enum_values: list[str] | None
    semantic: str


@dataclass
class ModuleSpec:
    """Top-level module metadata consumed by CLI and AI agents."""

    name: str
    category: str
    description: str
    tags: list[str]
    params: list[ParamSpec]
    inputs: list[str]
    outputs: list[str]
    cost_hint: str
    shader_path: str
    module_class: str


@dataclass(frozen=True)
class _DecoratorConfig:
    category: str
    description: str
    tags: tuple[str, ...]
    cost_hint: str


_registry: dict[str, ModuleSpec] = {}


def _type_to_string(annotation: Any) -> str:
    """Return a readable string for Python/typing annotations."""
    if annotation is inspect._empty:
        return "Any"
    if isinstance(annotation, str):
        return annotation
    if isinstance(annotation, type):
        return annotation.__name__

    origin = get_origin(annotation)
    if origin is None:
        return str(annotation).replace("typing.", "")

    args = get_args(annotation)
    origin_name = getattr(origin, "__name__", str(origin).replace("typing.", ""))
    if not args:
        return origin_name

    arg_text = ", ".join(_type_to_string(arg) for arg in args)
    return f"{origin_name}[{arg_text}]"


def _normalize_default(value: Any) -> Any:
    """Convert defaults into JSON-safe values when possible."""
    if isinstance(value, Enum):
        return value.name
    if isinstance(value, (str, int, float, bool, list, dict, tuple)) or value is None:
        return value
    return repr(value)


def _infer_semantic(name: str, type_text: str) -> str:
    """Infer a high-level semantic for a parameter."""
    lowered_name = name.lower()
    lowered_type = type_text.lower()

    if "texture" in lowered_name or "texture" in lowered_type:
        return "texture"
    if "audio" in lowered_name or "fft" in lowered_name:
        return "audio"
    if "bool" in lowered_type:
        return "toggle"
    if "int" in lowered_type or "float" in lowered_type:
        return "numeric"
    if "list" in lowered_type:
        return "array"
    return "generic"


def _extract_params_class(module_cls: type) -> type | None:
    """Resolve the Params generic type from ``BaseAVModule[Params, Uniforms]``."""
    for base in getattr(module_cls, "__orig_bases__", ()):
        args = get_args(base)
        if not args:
            continue
        param_cls = args[0]
        if isinstance(param_cls, type):
            return param_cls

    params_annotation = inspect.signature(module_cls.__init__).parameters.get("params")
    if params_annotation is not None and isinstance(params_annotation.annotation, type):
        return params_annotation.annotation
    return None


def _extract_params(module_cls: type) -> list[ParamSpec]:
    """Extract ``ParamSpec`` entries from a module class."""
    params_cls = _extract_params_class(module_cls)
    if params_cls is None:
        return []

    specs: list[ParamSpec] = []
    if is_dataclass(params_cls):
        for param in fields(params_cls):
            if param.name in _SKIP_PARAMS:
                continue

            default: Any = None
            if param.default is not MISSING:
                default = _normalize_default(param.default)
            elif param.default_factory is not MISSING:  # type: ignore[attr-defined]
                default = "<factory>"

            metadata = param.metadata or {}
            specs.append(
                ParamSpec(
                    name=param.name,
                    type=_type_to_string(param.type),
                    default=default,
                    min=metadata.get("min"),
                    max=metadata.get("max"),
                    description=metadata.get("description", ""),
                    enum_values=(
                        [str(item) for item in metadata.get("enum_values", [])]
                        if metadata.get("enum_values") is not None
                        else None
                    ),
                    semantic=_infer_semantic(param.name, _type_to_string(param.type)),
                )
            )
        return specs

    annotations = getattr(params_cls, "__annotations__", {})
    for name, annotation in annotations.items():
        if name in _SKIP_PARAMS:
            continue
        default = _normalize_default(getattr(params_cls, name, None))
        type_text = _type_to_string(annotation)
        specs.append(
            ParamSpec(
                name=name,
                type=type_text,
                default=default,
                min=None,
                max=None,
                description="",
                enum_values=None,
                semantic=_infer_semantic(name, type_text),
            )
        )
    return specs


def _normalize_tags(tags: Sequence[str]) -> list[str]:
    """Normalize and de-duplicate tag values while preserving order."""
    normalized: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        value = tag.strip()
        if not value:
            continue
        lowered = value.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(lowered)
    return normalized


def _build_spec(module_cls: type) -> ModuleSpec | None:
    """Build a ``ModuleSpec`` for a decorated module class."""
    config = getattr(module_cls, _REGISTRY_CONFIG_ATTR, None)
    if config is None:
        return None

    params = _extract_params(module_cls)
    input_params = [param.name for param in params if param.semantic in {"texture", "audio"}]
    shader_path = str(getattr(module_cls, "frag_shader_path", ""))
    return ModuleSpec(
        name=module_cls.__name__,
        category=config.category,
        description=config.description,
        tags=list(config.tags),
        params=params,
        inputs=input_params,
        outputs=["texture"],
        cost_hint=config.cost_hint,
        shader_path=shader_path,
        module_class=f"{module_cls.__module__}.{module_cls.__name__}",
    )


def _register_module(module_cls: type) -> None:
    """Register a decorated module class into the global registry."""
    spec = _build_spec(module_cls)
    if spec is None:
        return
    _registry[spec.name] = spec


def _register_decorated_classes(module: Any) -> None:
    """Register all decorated classes declared by a module object."""
    if module is None:
        return
    for _, member in inspect.getmembers(module, inspect.isclass):
        if member.__module__ != getattr(module, "__name__", ""):
            continue
        if hasattr(member, _REGISTRY_CONFIG_ATTR):
            _register_module(member)


def oblique_module(
    category: str,
    description: str,
    tags: Sequence[str],
    cost_hint: str,
) -> Callable[[type], type]:
    """Decorator used by AV modules to publish registry metadata."""
    normalized_tags = _normalize_tags(tags)
    config = _DecoratorConfig(
        category=category,
        description=description,
        tags=tuple(normalized_tags),
        cost_hint=cost_hint,
    )

    def _decorator(module_cls: type) -> type:
        setattr(module_cls, _REGISTRY_CONFIG_ATTR, config)
        _register_module(module_cls)
        return module_cls

    return _decorator


def discover_modules() -> dict[str, ModuleSpec]:
    """Discover and import all modules under ``modules`` and rebuild the registry."""
    import modules

    _registry.clear()
    _register_decorated_classes(modules)

    discovered: set[str] = set()
    for base_path in modules.__path__:
        root = Path(base_path)
        if not root.exists():
            continue

        search_dirs = [root]
        search_dirs.extend(path for path in root.rglob("*") if path.is_dir())
        for directory in search_dirs:
            relative = directory.relative_to(root)
            prefix = modules.__name__
            if relative.parts:
                prefix += "." + ".".join(relative.parts)
            prefix += "."

            for entry in pkgutil.walk_packages([str(directory)], prefix=prefix):
                if entry.ispkg:
                    continue
                if entry.name in discovered:
                    continue
                discovered.add(entry.name)

    for module_name in sorted(discovered):
        module = importlib.import_module(module_name)
        _register_decorated_classes(module)
    return dict(_registry)


def get_registry() -> dict[str, ModuleSpec]:
    """Return the current registry, auto-discovering modules if needed."""
    if not _registry:
        discover_modules()
    return dict(_registry)


def search_modules(
    query: str | None = None,
    tags: Sequence[str] | None = None,
    category: str | None = None,
) -> list[ModuleSpec]:
    """Search module specs by text query, tags, and/or category."""
    registry = get_registry()
    query_text = (query or "").strip().lower()
    wanted_tags = {tag.strip().lower() for tag in (tags or []) if tag.strip()}
    wanted_category = category.strip().lower() if category else None

    results: list[ModuleSpec] = []
    for spec in registry.values():
        if wanted_category and spec.category.lower() != wanted_category:
            continue

        spec_tags = {tag.lower() for tag in spec.tags}
        if wanted_tags and not wanted_tags.issubset(spec_tags):
            continue

        if query_text:
            haystack = " ".join([spec.name, spec.description, " ".join(spec.tags)]).lower()
            if query_text not in haystack:
                continue

        results.append(spec)

    return sorted(results, key=lambda spec: spec.name.lower())


def module_spec_to_dict(spec: ModuleSpec) -> dict[str, Any]:
    """Convert a ``ModuleSpec`` dataclass to a plain dictionary."""
    return asdict(spec)
