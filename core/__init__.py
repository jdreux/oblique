"""Core package exposing key classes with lazy imports."""

__all__ = ["ObliqueEngine", "ObliquePatch", "ObliqueNode"]


def __getattr__(name):
    if name == "ObliqueEngine":
        from .oblique_engine import ObliqueEngine
        return ObliqueEngine
    if name == "ObliquePatch":
        from .oblique_patch import ObliquePatch
        return ObliquePatch
    if name == "ObliqueNode":
        from .oblique_node import ObliqueNode
        return ObliqueNode
    raise AttributeError(name)
