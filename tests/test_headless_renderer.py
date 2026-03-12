"""Tests for HeadlessRenderer.

These tests use VisualNoise (no audio dependency) to verify the headless
rendering pipeline end-to-end on the real GPU via a standalone ModernGL context.

They require real GPU access and are skipped automatically when running alongside
tests that install moderngl stubs (e.g. unit tests for engine/renderer internals).
"""

import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

import moderngl

# Detect whether standalone GPU context creation is available.
# A real ``moderngl`` module can still fail in headless CI/sandbox environments.


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
_skip_if_no_gpu = pytest.mark.skipif(
    not _GPU_AVAILABLE, reason="Real GPU / standalone moderngl context not available"
)

from core.headless_renderer import HeadlessRenderer
from core.oblique_patch import ObliquePatch
from core.frame_analysis import analyze_frame, analyze_temporal, hash_distance, perceptual_hash
from modules.core.base_av_module import BaseAVModule, BaseAVParams, Uniforms
from modules.core.visual_noise import VisualNoiseModule, VisualNoiseParams


WIDTH, HEIGHT = 128, 128


def _noise_patch(width: int, height: int) -> ObliquePatch:
    """Minimal patch using VisualNoise — no audio, deterministic."""
    module = VisualNoiseModule(VisualNoiseParams(width=width, height=height))

    def tick(t: float) -> BaseAVModule:
        return module

    return ObliquePatch(tick_callback=tick)


def _rotating_rect_shader(shader_path: Path) -> None:
    shader_path.write_text(
        """
#version 330 core
uniform vec2 u_resolution;
uniform float u_time;
in vec2 v_uv;
out vec4 fragColor;

mat2 rot(float a) {
    float c = cos(a);
    float s = sin(a);
    return mat2(c, -s, s, c);
}

void main() {
    vec2 p = v_uv * 2.0 - 1.0;
    float angle = u_time * 0.78539816339; // 45 degrees / second
    vec2 q = rot(-angle) * p;
    vec2 half_size = vec2(0.45, 0.18);
    float inside = step(abs(q.x), half_size.x) * step(abs(q.y), half_size.y);
    fragColor = vec4(vec3(inside), 1.0);
}
        """.strip(),
        encoding="utf-8",
    )


def _rotating_rect_patch(width: int, height: int, shader_path: str) -> ObliquePatch:
    @dataclass
    class RotatingRectParams(BaseAVParams):
        width: int
        height: int

    class RotatingRectUniforms(Uniforms, total=True):
        u_time: float

    class RotatingRectModule(BaseAVModule[RotatingRectParams, RotatingRectUniforms]):
        frag_shader_path = "shaders/passthrough.frag"

        def __init__(self, params: RotatingRectParams, shader_file: str) -> None:
            self.frag_shader_path = shader_file
            super().__init__(params)

        def prepare_uniforms(self, t: float) -> RotatingRectUniforms:
            return {
                "u_resolution": (self.params.width, self.params.height),
                "u_time": t,
            }

    module = RotatingRectModule(
        RotatingRectParams(width=width, height=height),
        shader_path,
    )

    def tick(t: float) -> BaseAVModule:
        return module

    return ObliquePatch(tick_callback=tick)


def _dominant_axis_angle(arr: np.ndarray) -> float:
    """Return principal axis angle (radians) of bright pixels in a frame."""
    mask = arr[:, :, 0] > 0.5
    ys, xs = np.nonzero(mask)
    x = xs.astype(np.float32)
    y = ys.astype(np.float32)
    x -= x.mean()
    y -= y.mean()

    cov_xx = float(np.mean(x * x))
    cov_yy = float(np.mean(y * y))
    cov_xy = float(np.mean(x * y))
    angle = 0.5 * np.arctan2(2.0 * cov_xy, cov_xx - cov_yy)
    return float(abs(angle))


@pytest.fixture
def renderer():
    patch = _noise_patch(WIDTH, HEIGHT)
    r = HeadlessRenderer(patch, WIDTH, HEIGHT)
    yield r
    r.close()


@_skip_if_no_gpu
class TestRenderFrame:
    def test_shape(self, renderer):
        arr = renderer.render_frame(0.0)
        assert arr.shape == (HEIGHT, WIDTH, 4)

    def test_dtype(self, renderer):
        arr = renderer.render_frame(0.0)
        assert arr.dtype == np.float32

    def test_not_blank(self, renderer):
        arr = renderer.render_frame(0.5)
        assert arr.mean() > 0.0, "Expected non-blank output from VisualNoise"

    def test_values_in_range(self, renderer):
        arr = renderer.render_frame(0.0)
        assert arr.min() >= 0.0
        assert arr.max() <= 1.0


@_skip_if_no_gpu
class TestRenderToFile:
    def test_writes_png(self, renderer, tmp_path):
        dest = str(tmp_path / "frame.png")
        renderer.render_to_file(0.0, dest)
        assert os.path.isfile(dest)
        img = Image.open(dest)
        assert img.size == (WIDTH, HEIGHT)

    def test_rgba_mode(self, renderer, tmp_path):
        dest = str(tmp_path / "frame.png")
        renderer.render_to_file(0.0, dest)
        img = Image.open(dest)
        assert img.mode == "RGBA"


@_skip_if_no_gpu
class TestRenderSequence:
    def test_correct_file_count(self, renderer, tmp_path):
        times = [0.0, 0.5, 1.0, 1.5, 2.0]
        paths = renderer.render_sequence(times, str(tmp_path))
        assert len(paths) == len(times)
        for p in paths:
            assert os.path.isfile(p)

    def test_filenames_zero_padded(self, renderer, tmp_path):
        times = list(range(12))
        paths = renderer.render_sequence([float(t) for t in times], str(tmp_path))
        assert os.path.basename(paths[0]) == "frame_0000.png"
        assert os.path.basename(paths[11]) == "frame_0011.png"


@_skip_if_no_gpu
class TestInspect:
    def test_keys_present(self, renderer):
        stats = renderer.inspect(0.0)
        expected_keys = {
            "width",
            "height",
            "mean_brightness",
            "brightness_std",
            "non_black_ratio",
            "clipped_ratio",
            "mean_color_rgb",
            "color_variance",
            "mean_saturation",
            "dominant_hue",
            "edge_density",
            "spatial_balance",
            "center_brightness",
            "edge_brightness",
            "is_blank",
            "is_saturated",
            "is_dark",
            "has_color",
        }
        assert expected_keys.issubset(stats.keys())

    def test_dimensions_match(self, renderer):
        stats = renderer.inspect(0.0)
        assert stats["width"] == WIDTH
        assert stats["height"] == HEIGHT

    def test_non_blank(self, renderer):
        stats = renderer.inspect(0.5)
        assert stats["non_black_ratio"] > 0.0, "VisualNoise should produce non-black pixels"

    def test_inspect_sequence_includes_temporal_metrics(self, renderer):
        stats = renderer.inspect_sequence([0.0, 0.1, 0.2])
        expected = {"mean_motion", "motion_variance", "peak_motion", "is_static", "is_chaotic", "motion_profile"}
        assert expected.issubset(stats.keys())
        assert len(stats["motion_profile"]) == 2


@_skip_if_no_gpu
class TestContextManager:
    def test_context_manager(self):
        patch = _noise_patch(WIDTH, HEIGHT)
        with HeadlessRenderer(patch, WIDTH, HEIGHT) as r:
            arr = r.render_frame(0.0)
            assert arr.shape == (HEIGHT, WIDTH, 4)


@_skip_if_no_gpu
class TestPrimeAudio:
    def test_no_audio_is_safe(self, renderer):
        """prime_audio should be a no-op when the patch has no audio output."""
        renderer.prime_audio(t=1.0)  # should not raise


@_skip_if_no_gpu
class TestAnimatedRenderCycle:
    def test_rotating_rect_changes_over_time(self, tmp_path):
        shader_path = tmp_path / "rotating-rect.frag"
        _rotating_rect_shader(shader_path)
        patch = _rotating_rect_patch(WIDTH, HEIGHT, str(shader_path))

        with HeadlessRenderer(patch, WIDTH, HEIGHT) as renderer:
            frame_t0 = renderer.render_frame(0.0)
            frame_t1 = renderer.render_frame(1.0)

        stats_t0 = analyze_frame(frame_t0)
        stats_t1 = analyze_frame(frame_t1)
        temporal = analyze_temporal([frame_t0, frame_t1])

        assert stats_t0["is_blank"] is False
        assert stats_t1["is_blank"] is False
        assert abs(stats_t0["non_black_ratio"] - stats_t1["non_black_ratio"]) < 0.05
        assert temporal["mean_motion"] > 0.01

        h0 = perceptual_hash(frame_t0)
        h1 = perceptual_hash(frame_t1)
        assert hash_distance(h0, h1) >= 8

        angle_t0 = _dominant_axis_angle(frame_t0)
        angle_t1 = _dominant_axis_angle(frame_t1)
        assert angle_t0 < 0.2
        assert angle_t1 > 0.5
