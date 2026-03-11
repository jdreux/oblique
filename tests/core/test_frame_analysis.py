"""Unit tests for frame analysis helpers."""

from __future__ import annotations

import numpy as np
import pytest

from core.frame_analysis import analyze_frame, analyze_temporal, hash_distance, perceptual_hash


def _solid_frame(value: float, size: int = 16) -> np.ndarray:
    frame = np.zeros((size, size, 4), dtype=np.float32)
    frame[:, :, :3] = value
    frame[:, :, 3] = 1.0
    return frame


def test_analyze_frame_black() -> None:
    stats = analyze_frame(_solid_frame(0.0))
    assert stats["mean_brightness"] == pytest.approx(0.0)
    assert stats["non_black_ratio"] == pytest.approx(0.0)
    assert stats["is_blank"] is True
    assert stats["dominant_hue"] == "achromatic"
    assert stats["has_color"] is False


def test_analyze_frame_white() -> None:
    stats = analyze_frame(_solid_frame(1.0))
    assert stats["mean_brightness"] == pytest.approx(1.0)
    assert stats["clipped_ratio"] == pytest.approx(1.0)
    assert stats["is_saturated"] is True
    assert stats["non_black_ratio"] == pytest.approx(1.0)


def test_analyze_frame_half_red_half_blue() -> None:
    frame = np.zeros((32, 32, 4), dtype=np.float32)
    frame[:, :16, 0] = 1.0
    frame[:, 16:, 2] = 1.0
    frame[:, :, 3] = 1.0

    stats = analyze_frame(frame)
    assert stats["mean_color_rgb"] == pytest.approx([0.5, 0.0, 0.5], abs=1e-4)
    assert stats["has_color"] is True
    assert stats["dominant_hue"] in {"red", "blue"}
    assert stats["color_variance"] > 0.0


def test_analyze_frame_gradient() -> None:
    size = 32
    frame = np.zeros((size, size, 4), dtype=np.float32)
    ramp = np.linspace(0.0, 1.0, size, dtype=np.float32)
    frame[:, :, 0] = ramp[None, :]
    frame[:, :, 1] = ramp[None, :]
    frame[:, :, 2] = ramp[None, :]
    frame[:, :, 3] = 1.0

    stats = analyze_frame(frame)
    assert stats["brightness_std"] > 0.0
    assert stats["edge_density"] > 0.0
    assert 0.0 <= stats["spatial_balance"] <= 1.0


def test_analyze_temporal_static_frames() -> None:
    frame = _solid_frame(0.5)
    stats = analyze_temporal([frame, frame.copy(), frame.copy()])
    assert stats["mean_motion"] == pytest.approx(0.0)
    assert stats["is_static"] is True
    assert stats["motion_profile"] == pytest.approx([0.0, 0.0])


def test_analyze_temporal_motion_frames() -> None:
    dark = _solid_frame(0.0)
    bright = _solid_frame(1.0)
    stats = analyze_temporal([dark, bright])
    assert stats["mean_motion"] > 0.0
    assert stats["peak_motion"] == pytest.approx(stats["mean_motion"])
    assert stats["is_static"] is False
    assert len(stats["motion_profile"]) == 1


def test_perceptual_hash_is_stable() -> None:
    frame = _solid_frame(0.25, size=24)
    h1 = perceptual_hash(frame)
    h2 = perceptual_hash(frame.copy())
    assert h1 == h2
    assert hash_distance(h1, h2) == 0


def test_hash_distance_requires_equal_lengths() -> None:
    with pytest.raises(ValueError):
        hash_distance("0101", "010")
