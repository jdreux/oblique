"""Frame analysis utilities for headless rendering inspection.

All routines in this module are pure NumPy and operate on RGBA float arrays
with shape ``(H, W, 4)`` and values in ``[0, 1]``.
"""

from __future__ import annotations

from typing import Any

import numpy as np

_LUMA_WEIGHTS = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
_HUE_NAMES = [
    "red",
    "orange",
    "yellow",
    "chartreuse",
    "green",
    "spring",
    "cyan",
    "azure",
    "blue",
    "violet",
    "magenta",
    "rose",
]


def _validate_frame(arr: np.ndarray) -> None:
    """Validate that *arr* is an ``(H, W, 4)`` array."""
    if arr.ndim != 3 or arr.shape[2] < 3:
        raise ValueError("Expected frame with shape (H, W, 4) or (H, W, >=3).")


def _luminance(rgb: np.ndarray) -> np.ndarray:
    """Compute perceptual luminance from RGB channels."""
    return np.tensordot(rgb, _LUMA_WEIGHTS, axes=([-1], [0])).astype(np.float32)


def _hue_saturation(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return hue and saturation maps for RGB input."""
    maxc = rgb.max(axis=2)
    minc = rgb.min(axis=2)
    delta = maxc - minc

    saturation = np.zeros_like(maxc, dtype=np.float32)
    non_zero = maxc > 1e-8
    saturation[non_zero] = delta[non_zero] / maxc[non_zero]

    hue = np.zeros_like(maxc, dtype=np.float32)
    delta_non_zero = delta > 1e-8

    r = rgb[:, :, 0]
    g = rgb[:, :, 1]
    b = rgb[:, :, 2]

    r_max = delta_non_zero & (maxc == r)
    g_max = delta_non_zero & (maxc == g)
    b_max = delta_non_zero & (maxc == b)

    hue[r_max] = ((g[r_max] - b[r_max]) / delta[r_max]) % 6.0
    hue[g_max] = ((b[g_max] - r[g_max]) / delta[g_max]) + 2.0
    hue[b_max] = ((r[b_max] - g[b_max]) / delta[b_max]) + 4.0
    hue = (hue / 6.0) % 1.0
    return hue.astype(np.float32), saturation


def _spatial_masks(height: int, width: int) -> tuple[np.ndarray, np.ndarray]:
    """Return center and edge masks from normalized radial distance."""
    ys = np.linspace(0.0, 1.0, height, endpoint=False) + (0.5 / max(1, height))
    xs = np.linspace(0.0, 1.0, width, endpoint=False) + (0.5 / max(1, width))
    grid_y, grid_x = np.meshgrid(ys, xs, indexing="ij")

    dx = grid_x - 0.5
    dy = grid_y - 0.5
    radius = np.sqrt(dx * dx + dy * dy) / np.sqrt(0.5)
    center_mask = radius < 0.3
    edge_mask = radius > 0.7
    return center_mask, edge_mask


def analyze_frame(arr: np.ndarray) -> dict[str, Any]:
    """Compute descriptive visual metrics for a single frame."""
    _validate_frame(arr)
    rgb = np.clip(arr[:, :, :3], 0.0, 1.0).astype(np.float32)
    luminance = _luminance(rgb)

    mean_brightness = float(luminance.mean())
    brightness_std = float(luminance.std())
    non_black_ratio = float((luminance > 0.01).mean())
    clipped_ratio = float((luminance > 0.99).mean())
    mean_color_rgb = [float(v) for v in rgb.mean(axis=(0, 1))]
    color_variance = float(rgb.var(axis=(0, 1)).mean())

    hue, saturation = _hue_saturation(rgb)
    mean_saturation = float(saturation.mean())
    if mean_saturation <= 0.1:
        dominant_hue = "achromatic"
    else:
        mask = saturation > 0.1
        if not np.any(mask):
            dominant_hue = "achromatic"
        else:
            hist, _ = np.histogram(hue[mask], bins=12, range=(0.0, 1.0))
            dominant_hue = _HUE_NAMES[int(np.argmax(hist))]

    if arr.shape[1] < 3:
        edge_density = 0.0
    else:
        edge_density = float(np.abs(luminance[:, 2:] - luminance[:, :-2]).mean())

    height, width = luminance.shape
    y_mid = height // 2
    x_mid = width // 2
    quadrants = [
        luminance[:y_mid, :x_mid],
        luminance[:y_mid, x_mid:],
        luminance[y_mid:, :x_mid],
        luminance[y_mid:, x_mid:],
    ]
    quad_means = [float(quad.mean()) if quad.size else mean_brightness for quad in quadrants]
    spatial_balance = float(1.0 - (max(quad_means) - min(quad_means)))

    center_mask, edge_mask = _spatial_masks(height, width)
    center_brightness = float(luminance[center_mask].mean()) if np.any(center_mask) else mean_brightness
    edge_brightness = float(luminance[edge_mask].mean()) if np.any(edge_mask) else mean_brightness

    return {
        "mean_brightness": mean_brightness,
        "brightness_std": brightness_std,
        "non_black_ratio": non_black_ratio,
        "clipped_ratio": clipped_ratio,
        "mean_color_rgb": mean_color_rgb,
        "color_variance": color_variance,
        "mean_saturation": mean_saturation,
        "dominant_hue": dominant_hue,
        "edge_density": edge_density,
        "spatial_balance": spatial_balance,
        "center_brightness": center_brightness,
        "edge_brightness": edge_brightness,
        "is_blank": mean_brightness < 0.005,
        "is_saturated": clipped_ratio > 0.5,
        "is_dark": mean_brightness < 0.1,
        "has_color": mean_saturation > 0.1,
    }


def analyze_temporal(frames: list[np.ndarray]) -> dict[str, Any]:
    """Compute temporal motion metrics across a list of frames."""
    if len(frames) < 2:
        return {
            "mean_motion": 0.0,
            "motion_variance": 0.0,
            "peak_motion": 0.0,
            "is_static": True,
            "is_chaotic": False,
            "motion_profile": [],
        }

    motion_profile: list[float] = []
    for prev, curr in zip(frames, frames[1:]):
        _validate_frame(prev)
        _validate_frame(curr)
        prev_rgb = np.clip(prev[:, :, :3], 0.0, 1.0).astype(np.float32)
        curr_rgb = np.clip(curr[:, :, :3], 0.0, 1.0).astype(np.float32)
        motion_profile.append(float(np.abs(curr_rgb - prev_rgb).mean()))

    motion_arr = np.array(motion_profile, dtype=np.float32)
    mean_motion = float(motion_arr.mean())
    motion_variance = float(motion_arr.var())
    peak_motion = float(motion_arr.max())
    return {
        "mean_motion": mean_motion,
        "motion_variance": motion_variance,
        "peak_motion": peak_motion,
        "is_static": mean_motion < 0.001,
        "is_chaotic": motion_variance > 0.01,
        "motion_profile": motion_profile,
    }


def perceptual_hash(arr: np.ndarray, hash_size: int = 8) -> str:
    """Compute a simple average hash bitstring for the given frame."""
    _validate_frame(arr)
    if hash_size <= 0:
        raise ValueError("hash_size must be > 0")

    rgb = np.clip(arr[:, :, :3], 0.0, 1.0).astype(np.float32)
    gray = _luminance(rgb)
    y_idx = np.linspace(0, gray.shape[0] - 1, hash_size).astype(int)
    x_idx = np.linspace(0, gray.shape[1] - 1, hash_size).astype(int)
    small = gray[np.ix_(y_idx, x_idx)]

    mean_val = float(small.mean())
    bits = (small > mean_val).astype(np.uint8).reshape(-1)
    return "".join("1" if bit else "0" for bit in bits)


def hash_distance(h1: str, h2: str) -> int:
    """Return Hamming distance between two equal-length bitstrings."""
    if len(h1) != len(h2):
        raise ValueError("Hashes must have the same length.")
    return sum(ch1 != ch2 for ch1, ch2 in zip(h1, h2))
