from dataclasses import dataclass
from typing import Tuple

import moderngl

from modules.base_av_module import BaseAVModule, BaseAVParams, ParamFloat, ParamInt, ParamTexture, Uniforms


@dataclass
class GridSwapModuleParams(BaseAVParams):
    swapped_texture: ParamTexture 
    grid_size: ParamInt = 8  # NxN grid size
    swap_frequency: ParamFloat = 1.0  # How often swaps occur (in Hz)
    swap_phase: ParamFloat = 0.0  # Phase offset for swap timing
    num_swaps: ParamInt = 8

class GridSwapModuleUniforms(Uniforms, total=True):
    u_time: float
    u_resolution: Tuple[int, int]
    u_grid_size: int
    u_swap_frequency: float
    u_swap_phase: float
    u_num_swaps: int
    tex0: BaseAVModule


class GridSwapModule(BaseAVModule[GridSwapModuleParams, GridSwapModuleUniforms]):
    """
    Grid Swap Module - Takes a texture input and performs square swapping operations on an NxN grid.
    Inspired by Ryoji Ikeda's geometric manipulations.
    """

    metadata = {
        "name": "GridSwapModule",
        "description": "Takes a texture input and performs square swapping operations on an NxN grid.",
        "parameters": GridSwapModuleParams.__annotations__,
    }
    frag_shader_path: str = "shaders/grid-swap-module.frag"

    def __init__(self, params: GridSwapModuleParams):
        """
        Initialize GridSwapModule module.
        Args:
            params (GridSwapModuleParams): Parameters for the module.
            module (BaseAVModule): Upstream module to get texture from.
        """
        super().__init__(params)

    def prepare_uniforms(self, t: float) -> GridSwapModuleUniforms:
        """
        Return the uniforms needed for rendering.
        """
        uniforms: GridSwapModuleUniforms = {
            "u_time": t,
            "u_resolution": (self._resolve_param(self.params.width), self._resolve_param(self.params.height)),
            "u_grid_size": self._resolve_param(self.params.grid_size),
            "u_swap_frequency": self._resolve_param(self.params.swap_frequency),
            "u_swap_phase": self._resolve_param(self.params.swap_phase),
            "u_num_swaps": self._resolve_param(self.params.num_swaps),
            "tex0": self.params.swapped_texture,
        }
        return uniforms