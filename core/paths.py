"""Utility helpers for locating installed Oblique assets.

These helpers provide absolute paths to data files bundled with the
installation—fragment shaders, demo patches, templates, etc.  Everything is
resolved relative to the package root so the CLI works whether it is executed
from a cloned repository or from an installed wheel/homebrew package.
"""

from __future__ import annotations

from pathlib import Path


_PACKAGE_ROOT = Path(__file__).resolve().parent.parent


def package_root() -> Path:
    """Return the root directory that contains the Oblique packages and assets."""

    return _PACKAGE_ROOT


def resolve_asset_path(relative_path: str | Path) -> Path:
    """Resolve an asset path relative to the installed package root.

    Args:
        relative_path: Path to the asset relative to the repository/package root.

    Returns:
        Absolute :class:`Path` to the requested asset.  Absolute inputs are
        returned unchanged.
    """

    path = Path(relative_path)
    if path.is_absolute():
        return path
    return _PACKAGE_ROOT / path
