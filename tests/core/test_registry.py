import sys
import types
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from tests.utils.stubs import load_module, setup_stubs


ROOT = Path(__file__).resolve().parents[2]


def _ensure_processing_package() -> None:
    processing = sys.modules.get("processing")
    if processing is not None and hasattr(processing, "__path__"):
        return

    processing_pkg = types.ModuleType("processing")
    processing_pkg.__path__ = [str(ROOT / "processing")]
    sys.modules["processing"] = processing_pkg


def test_discover_modules_registers_decorated_classes() -> None:
    setup_stubs()
    _ensure_processing_package()
    registry = load_module("core.registry", ROOT / "core/registry.py")

    specs = registry.discover_modules()
    assert len(specs) >= 22
    assert "FeedbackModule" in specs
    assert "CompositeModule" in specs
    assert "CircleEcho" in specs

    feedback_spec = specs["FeedbackModule"]
    assert feedback_spec.category == "effects"
    assert feedback_spec.module_class.endswith("FeedbackModule")
    assert all(param.name not in {"width", "height"} for param in feedback_spec.params)


def test_search_modules_filters_query_tag_and_category() -> None:
    setup_stubs()
    _ensure_processing_package()
    registry = load_module("core.registry", ROOT / "core/registry.py")
    registry.discover_modules()

    feedback_matches = registry.search_modules(query="feedback", tags=None, category=None)
    feedback_names = {spec.name for spec in feedback_matches}
    assert "FeedbackModule" in feedback_names

    audio_matches = registry.search_modules(
        query=None,
        tags=["audio-reactive"],
        category="audio_reactive",
    )
    assert any(spec.name == "CircleEcho" for spec in audio_matches)


def test_module_spec_to_dict_contains_expected_keys() -> None:
    setup_stubs()
    _ensure_processing_package()
    registry = load_module("core.registry", ROOT / "core/registry.py")
    specs = registry.discover_modules()

    payload = registry.module_spec_to_dict(specs["CompositeModule"])
    assert payload["name"] == "CompositeModule"
    assert payload["category"] == "composition"
    assert "params" in payload
    assert "tags" in payload


def test_numeric_params_expose_ranges_for_annotated_modules() -> None:
    setup_stubs()
    _ensure_processing_package()
    registry = load_module("core.registry", ROOT / "core/registry.py")
    specs = registry.discover_modules()

    annotated_modules = {
        "VisualNoiseModule",
        "MediaModule",
        "CircleEcho",
        "RyojiLines",
        "SpectralVisualizerModule",
        "MITParticlesModule",
        "ProtoplasmModule",
        "GridSwapModule",
        "PauricSquaresModule",
        "BrokenCirclesModule",
        "BlueBackNGrayModule",
        "IkedaTestPatternModule",
        "IkedaTinyBarcodeModule",
        "MeshShroudModule",
        "FeedbackModule",
        "BlurModule",
        "BarrelDistortionModule",
        "LevelModule",
        "CompositeModule",
        "TransformModule",
        "DebugModule",
        "ShadertoyModule",
    }

    for module_name in annotated_modules:
        assert module_name in specs
        spec = specs[module_name]
        for param in spec.params:
            if param.semantic != "numeric":
                continue
            assert param.min is not None, f"{module_name}.{param.name} missing min"
            assert param.max is not None, f"{module_name}.{param.name} missing max"
            assert param.description.strip(), f"{module_name}.{param.name} missing description"


def test_enum_metadata_is_preserved_in_registry() -> None:
    setup_stubs()
    _ensure_processing_package()
    registry = load_module("core.registry", ROOT / "core/registry.py")
    specs = registry.discover_modules()

    visual_noise = specs["VisualNoiseModule"]
    noise_size = next(param for param in visual_noise.params if param.name == "noise_size")
    color_mode = next(param for param in visual_noise.params if param.name == "color_mode")
    assert noise_size.enum_values == ["small", "medium", "large"]
    assert color_mode.enum_values == ["gray", "rgba"]

    composite = specs["CompositeModule"]
    operation = next(param for param in composite.params if param.name == "operation")
    assert operation.enum_values is not None
    assert "add" in operation.enum_values
