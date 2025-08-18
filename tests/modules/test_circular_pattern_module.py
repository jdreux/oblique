from modules.effects.circular_pattern import (
    CircularPatternModule,
    CircularPatternParams,
)


def test_circular_pattern_uniforms() -> None:
    params = CircularPatternParams(width=640, height=480)
    module = CircularPatternModule(params)
    uniforms = module.prepare_uniforms(1.0)
    assert uniforms["u_resolution"] == (640, 480)
    assert "u_ring_count" in uniforms
    assert "u_segment_count" in uniforms
