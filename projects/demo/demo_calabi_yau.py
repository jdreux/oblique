from core.oblique_patch import ObliquePatch
from modules.generative.calabi_yau import CalabiYau, CalabiYauParams


def oblique_patch(width: int, height: int) -> ObliquePatch:
    cy = CalabiYau(CalabiYauParams(width=width, height=height))

    def tick(t: float):
        return cy

    return ObliquePatch(tick_callback=tick)
