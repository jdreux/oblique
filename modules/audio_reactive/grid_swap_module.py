from dataclasses import dataclass, field
from typing import Tuple

import moderngl

from core.registry import oblique_module
from modules.core.base_av_module import BaseAVModule, BaseAVParams, ParamFloat, ParamInt, ParamTexture, Uniforms


@dataclass
class GridSwapModuleParams(BaseAVParams):
    swapped_texture: ParamTexture = field(
        metadata={
            "description": "Input texture whose grid cells are swapped.",
        }
    )
    grid_size: ParamInt = field(
        default=8,
        metadata={
            "min": 1,
            "max": 64,
            "description": "Number of cells per axis in the swap grid.",
        },
    )
    swap_frequency: ParamFloat = field(
        default=1.0,
        metadata={
            "min": 0.0,
            "max": 20.0,
            "description": "Swap cadence in Hz.",
        },
    )
    swap_phase: ParamFloat = field(
        default=0.0,
        metadata={
            "min": 0.0,
            "max": 6.2832,
            "description": "Phase offset applied to swap timing.",
        },
    )
    num_swaps: ParamInt = field(
        default=8,
        metadata={
            "min": 1,
            "max": 64,
            "description": "Number of swap pairs applied each frame.",
        },
    )

class GridSwapModuleUniforms(Uniforms, total=True):
    u_time: float
    u_resolution: Tuple[int, int]
    u_grid_size: int
    u_swap_frequency: float
    u_swap_phase: float
    u_num_swaps: int
    u_tex0: moderngl.Texture


@oblique_module(
    category="audio_reactive",
    description="Swaps grid cells between source textures with rhythmic timing controls.",
    tags=["geometric", "glitch", "audio-reactive", "rhythmic"],
    cost_hint="medium",
)
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
    frag_shader_path: str = "modules/audio_reactive/shaders/grid-swap-module.frag"

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
            "u_tex0": self.params.swapped_texture,
        }
        return uniforms
