"""Tests for HeadlessRenderer.

These tests use VisualNoise (no audio dependency) to verify the headless
rendering pipeline end-to-end on the real GPU via a standalone ModernGL context.

They require real GPU access and are skipped automatically when running alongside
tests that install moderngl stubs (e.g. unit tests for engine/renderer internals).
"""

import os

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
from modules.core.base_av_module import BaseAVModule
from modules.core.visual_noise import VisualNoiseModule, VisualNoiseParams


WIDTH, HEIGHT = 128, 128


def _noise_patch(width: int, height: int) -> ObliquePatch:
    """Minimal patch using VisualNoise — no audio, deterministic."""
    module = VisualNoiseModule(VisualNoiseParams(width=width, height=height))

    def tick(t: float) -> BaseAVModule:
        return module

    return ObliquePatch(tick_callback=tick)


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
        assert set(stats.keys()) == {"width", "height", "mean_brightness", "non_black_ratio"}

    def test_dimensions_match(self, renderer):
        stats = renderer.inspect(0.0)
        assert stats["width"] == WIDTH
        assert stats["height"] == HEIGHT

    def test_non_blank(self, renderer):
        stats = renderer.inspect(0.5)
        assert stats["non_black_ratio"] > 0.0, "VisualNoise should produce non-black pixels"


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
