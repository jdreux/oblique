"""Tests for the .to() / .mix() chainable composition API on BaseAVModule."""
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

import pytest

from core.paths import resolve_asset_path
from tests.utils.stubs import load_module, setup_stubs


def _get_base_mod():
    setup_stubs()
    base_mod = sys.modules.get("modules.core.base_av_module")
    if base_mod is None:
        base_mod = load_module(
            "modules.core.base_av_module",
            ROOT / "modules/core/base_av_module.py",
        )
    return base_mod


def _make_source(base_mod, w=800, h=600):
    """Create a simple source module (generator, no texture input)."""
    BaseAVModule = base_mod.BaseAVModule
    BaseAVParams = base_mod.BaseAVParams
    Uniforms = base_mod.Uniforms

    @dataclass
    class SourceParams(BaseAVParams):
        pass

    class SourceModule(BaseAVModule[SourceParams, Uniforms]):
        frag_shader_path = str(resolve_asset_path("shaders/passthrough.frag"))

        def prepare_uniforms(self, t: float) -> Uniforms:
            return {"u_resolution": (self.params.width, self.params.height)}

    return SourceModule(SourceParams(width=w, height=h))


def _make_effect_cls(base_mod, field_name="input_texture"):
    """Create an effect module class with a configurable texture input field name."""
    BaseAVModule = base_mod.BaseAVModule
    BaseAVParams = base_mod.BaseAVParams
    ParamTexture = base_mod.ParamTexture
    ParamFloat = base_mod.ParamFloat
    Uniforms = base_mod.Uniforms

    if field_name == "input_texture":

        @dataclass
        class EffectParams(BaseAVParams):
            input_texture: ParamTexture = None
            strength: ParamFloat = 0.5

        class EffectModule(BaseAVModule[EffectParams, Uniforms]):
            frag_shader_path = str(resolve_asset_path("shaders/passthrough.frag"))

            def prepare_uniforms(self, t: float) -> Uniforms:
                return {
                    "u_resolution": (self.params.width, self.params.height),
                    "u_texture": self.params.input_texture,
                    "u_strength": self.params.strength,
                }

        return EffectModule, EffectParams

    elif field_name == "parent_module":

        @dataclass
        class LevelLikeParams(BaseAVParams):
            parent_module: BaseAVModule = None
            contrast: ParamFloat = 1.0

        class LevelLikeModule(BaseAVModule[LevelLikeParams, Uniforms]):
            frag_shader_path = str(resolve_asset_path("shaders/passthrough.frag"))

            def prepare_uniforms(self, t: float) -> Uniforms:
                return {
                    "u_resolution": (self.params.width, self.params.height),
                    "u_texture": self.params.parent_module,
                }

        return LevelLikeModule, LevelLikeParams

    elif field_name == "motif_texture":

        @dataclass
        class MotifParams(BaseAVParams):
            motif_texture: ParamTexture = None
            tile_size: int = 8

        class MotifModule(BaseAVModule[MotifParams, Uniforms]):
            frag_shader_path = str(resolve_asset_path("shaders/passthrough.frag"))

            def prepare_uniforms(self, t: float) -> Uniforms:
                return {
                    "u_resolution": (self.params.width, self.params.height),
                    "u_texture": self.params.motif_texture,
                }

        return MotifModule, MotifParams


# ------------------------------------------------------------------
# .to() tests
# ------------------------------------------------------------------


class TestTo:

    def test_basic_chain(self):
        base_mod = _get_base_mod()
        source = _make_source(base_mod)
        EffectModule, EffectParams = _make_effect_cls(base_mod)

        result = source.to(EffectModule, strength=0.8)

        assert isinstance(result, EffectModule)
        assert result.params.input_texture is source
        assert result.params.strength == 0.8

    def test_inherits_resolution(self):
        base_mod = _get_base_mod()
        source = _make_source(base_mod, w=1920, h=1080)
        EffectModule, _ = _make_effect_cls(base_mod)

        result = source.to(EffectModule)

        assert result.params.width == 1920
        assert result.params.height == 1080

    def test_resolution_override(self):
        base_mod = _get_base_mod()
        source = _make_source(base_mod, w=1920, h=1080)
        EffectModule, _ = _make_effect_cls(base_mod)

        result = source.to(EffectModule, width=800, height=600)

        assert result.params.width == 800
        assert result.params.height == 600

    def test_multi_step_chain(self):
        base_mod = _get_base_mod()
        source = _make_source(base_mod)
        EffectModule, _ = _make_effect_cls(base_mod)

        result = (
            source
            .to(EffectModule, strength=0.1)
            .to(EffectModule, strength=0.2)
            .to(EffectModule, strength=0.3)
        )

        # Final module's input is the middle module
        assert isinstance(result, EffectModule)
        assert result.params.strength == 0.3
        middle = result.params.input_texture
        assert isinstance(middle, EffectModule)
        assert middle.params.strength == 0.2
        first = middle.params.input_texture
        assert isinstance(first, EffectModule)
        assert first.params.strength == 0.1
        assert first.params.input_texture is source

    def test_parent_module_field(self):
        """LevelModule uses parent_module instead of input_texture."""
        base_mod = _get_base_mod()
        source = _make_source(base_mod)
        LevelLike, _ = _make_effect_cls(base_mod, field_name="parent_module")

        result = source.to(LevelLike, contrast=2.0)

        assert result.params.parent_module is source
        assert result.params.contrast == 2.0

    def test_motif_texture_field(self):
        """PauricSquaresModule uses motif_texture."""
        base_mod = _get_base_mod()
        source = _make_source(base_mod)
        MotifModule, _ = _make_effect_cls(base_mod, field_name="motif_texture")

        result = source.to(MotifModule, tile_size=16)

        assert result.params.motif_texture is source
        assert result.params.tile_size == 16

    def test_explicit_texture_overrides_autowire(self):
        base_mod = _get_base_mod()
        source = _make_source(base_mod)
        other = _make_source(base_mod)
        EffectModule, _ = _make_effect_cls(base_mod)

        result = source.to(EffectModule, input_texture=other)

        assert result.params.input_texture is other

    def test_no_texture_field_raises(self):
        base_mod = _get_base_mod()
        BaseAVModule = base_mod.BaseAVModule
        BaseAVParams = base_mod.BaseAVParams
        Uniforms = base_mod.Uniforms

        @dataclass
        class NoTextureParams(BaseAVParams):
            speed: float = 1.0

        class GeneratorModule(BaseAVModule[NoTextureParams, Uniforms]):
            frag_shader_path = str(resolve_asset_path("shaders/passthrough.frag"))

            def prepare_uniforms(self, t: float) -> Uniforms:
                return {}

        source = _make_source(base_mod)
        with pytest.raises(TypeError, match="no ParamTexture"):
            source.to(GeneratorModule)


# ------------------------------------------------------------------
# .mix() tests
# ------------------------------------------------------------------


class TestMix:

    def test_basic_mix(self):
        base_mod = _get_base_mod()
        setup_stubs()
        # Need CompositeModule loaded
        comp_mod = load_module(
            "modules.composition.composite_module",
            ROOT / "modules/composition/composite_module.py",
        )
        CompositeModule = comp_mod.CompositeModule
        CompositeOp = comp_mod.CompositeOp

        a = _make_source(base_mod)
        b = _make_source(base_mod)

        result = a.mix(b, amount=0.7, op=CompositeOp.ADD)

        assert isinstance(result, CompositeModule)
        assert result.params.top_texture is a
        assert result.params.bottom_texture is b
        assert result.params.mix == 0.7
        assert result.params.operation == CompositeOp.ADD

    def test_mix_defaults(self):
        base_mod = _get_base_mod()
        setup_stubs()
        comp_mod = load_module(
            "modules.composition.composite_module",
            ROOT / "modules/composition/composite_module.py",
        )
        CompositeModule = comp_mod.CompositeModule
        CompositeOp = comp_mod.CompositeOp

        a = _make_source(base_mod)
        b = _make_source(base_mod)

        result = a.mix(b)

        assert isinstance(result, CompositeModule)
        assert result.params.mix == 0.5
        assert result.params.operation == CompositeOp.SCREEN

    def test_mix_inherits_resolution(self):
        base_mod = _get_base_mod()
        setup_stubs()
        load_module(
            "modules.composition.composite_module",
            ROOT / "modules/composition/composite_module.py",
        )

        a = _make_source(base_mod, w=1920, h=1080)
        b = _make_source(base_mod)

        result = a.mix(b)

        assert result.params.width == 1920
        assert result.params.height == 1080

    def test_mix_is_chainable(self):
        base_mod = _get_base_mod()
        setup_stubs()
        load_module(
            "modules.composition.composite_module",
            ROOT / "modules/composition/composite_module.py",
        )
        EffectModule, _ = _make_effect_cls(base_mod)

        a = _make_source(base_mod)
        b = _make_source(base_mod)

        result = a.mix(b).to(EffectModule, strength=0.9)

        assert isinstance(result, EffectModule)
        assert result.params.strength == 0.9


# ------------------------------------------------------------------
# .to() + .mix() combined
# ------------------------------------------------------------------


class TestChainedComposition:

    def test_to_then_mix(self):
        base_mod = _get_base_mod()
        setup_stubs()
        load_module(
            "modules.composition.composite_module",
            ROOT / "modules/composition/composite_module.py",
        )
        EffectModule, _ = _make_effect_cls(base_mod)

        source = _make_source(base_mod)
        background = _make_source(base_mod)

        result = (
            source
            .to(EffectModule, strength=0.5)
            .to(EffectModule, strength=0.9)
            .mix(background, amount=0.8)
        )

        # result is a CompositeModule
        from modules.composition.composite_module import CompositeModule
        assert isinstance(result, CompositeModule)
        assert result.params.mix == 0.8
        # top_texture is the end of the effect chain
        top = result.params.top_texture
        assert isinstance(top, EffectModule)
        assert top.params.strength == 0.9

    def test_full_pipeline(self):
        """End-to-end: source → effect → effect → mix → effect."""
        base_mod = _get_base_mod()
        setup_stubs()
        load_module(
            "modules.composition.composite_module",
            ROOT / "modules/composition/composite_module.py",
        )
        EffectModule, _ = _make_effect_cls(base_mod)

        source = _make_source(base_mod)
        bg = _make_source(base_mod)

        result = (
            source
            .to(EffectModule, strength=0.1)
            .to(EffectModule, strength=0.2)
            .mix(bg, amount=0.5)
            .to(EffectModule, strength=0.3)
        )

        assert isinstance(result, EffectModule)
        assert result.params.strength == 0.3
