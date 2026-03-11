from pathlib import Path
import sys

from tests.utils.stubs import load_module, setup_stubs


ROOT = Path(__file__).resolve().parents[2]


def test_texture_uniforms_use_moderngl_texture_type():
    setup_stubs()
    texture_type = sys.modules["moderngl"].Texture

    composite = load_module(
        "modules.composition.composite_module",
        ROOT / "modules/composition/composite_module.py",
    )
    feedback = load_module(
        "modules.effects.feedback",
        ROOT / "modules/effects/feedback.py",
    )
    transform = load_module(
        "modules.utility.transform",
        ROOT / "modules/utility/transform.py",
    )
    blur = load_module(
        "modules.effects.blur_module",
        ROOT / "modules/effects/blur_module.py",
    )
    level = load_module(
        "modules.effects.level_module",
        ROOT / "modules/effects/level_module.py",
    )
    barrel = load_module(
        "modules.effects.barrel_distortion",
        ROOT / "modules/effects/barrel_distortion.py",
    )
    grid_swap = load_module(
        "modules.audio_reactive.grid_swap_module",
        ROOT / "modules/audio_reactive/grid_swap_module.py",
    )
    pauric = load_module(
        "modules.audio_reactive.pauric_squares_module",
        ROOT / "modules/audio_reactive/pauric_squares_module.py",
    )
    media = load_module(
        "modules.core.media_module",
        ROOT / "modules/core/media_module.py",
    )

    assert composite.CompositeUniforms.__annotations__["u_top_tex"] is texture_type
    assert composite.CompositeUniforms.__annotations__["u_bottom_tex"] is texture_type
    assert feedback.FeedbackUniforms.__annotations__["u_input_texture"] is texture_type
    assert transform.TransformUniforms.__annotations__["u_texture"] is texture_type
    assert blur.BlurUniforms.__annotations__["u_input_texture"] is texture_type
    assert level.LevelUniforms.__annotations__["u_texture"] is texture_type
    assert barrel.BarrelDistortionUniforms.__annotations__["u_texture"] is texture_type
    assert grid_swap.GridSwapModuleUniforms.__annotations__["u_tex0"] is texture_type
    assert pauric.PauricSquaresUniforms.__annotations__["u_texture"] is texture_type
    assert media.MediaUniforms.__annotations__["u_tex"] is texture_type
