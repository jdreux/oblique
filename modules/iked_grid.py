from dataclasses import dataclass
from typing import Any, Tuple, Optional, List
from modules.base_av_module import BaseAVModule, Uniforms, BaseAVParams
import moderngl

@dataclass
class IkedGridParams(BaseAVParams):
    grid_size: int = 8  # NxN grid size
    swap_pairs: Optional[List[Tuple[int, int, int, int]]] = None  # List of (x1, y1, x2, y2) swap pairs
    swap_frequency: float = 1.0  # How often swaps occur (in Hz)
    swap_phase: float = 0.0  # Phase offset for swap timing

class IkedGridUniforms(Uniforms, total=True):
    u_time: float
    u_resolution: Tuple[int, int]
    u_grid_size: int
    u_swap_frequency: float
    u_swap_phase: float
    # u_swap_pairs: List[Tuple[int, int, int, int]]
    tex0: moderngl.Texture

class IkedGrid(BaseAVModule[IkedGridParams]):
    """
    Ikeda Grid - Takes a texture input and performs square swapping operations on an NxN grid.
    Inspired by Ryoji Ikeda's geometric manipulations.
    """
    metadata = {
        'name': 'IkedGrid',
        'description': 'Takes a texture input and performs square swapping operations on an NxN grid.',
        'parameters': IkedGridParams.__annotations__,
    }
    frag_shader_path: str = 'shaders/iked-grid.frag'

    def __init__(self, params: IkedGridParams, module: BaseAVModule):
        """
        Initialize IkedGrid module.
        Args:
            params (IkedGridParams): Parameters for the module.
            module (BaseAVModule): Upstream module to get texture from.
        """
        super().__init__(params)
        self.width = self.params.width
        self.height = self.params.height
        self.grid_size = self.params.grid_size
        self.swap_frequency = self.params.swap_frequency
        self.swap_phase = self.params.swap_phase
        self.upstream_module = module

        # Initialize default swap pairs if none provided
        if self.params.swap_pairs is None:
            # Default: swap corners and some middle squares
            self.swap_pairs = [
                (0, 0, self.grid_size-1, self.grid_size-1),  # Top-left with bottom-right
                (0, self.grid_size-1, self.grid_size-1, 0),  # Top-right with bottom-left
                (self.grid_size//2, self.grid_size//2, self.grid_size//2-1, self.grid_size//2-1),  # Center squares
            ]
        else:
            self.swap_pairs = self.params.swap_pairs

    def render_data(self, t: float) -> dict[str, Any]:
        """
        Return the data needed for the renderer to render this module.
        """
        # Convert swap pairs to shader-compatible format
        # Shader expects vec4 array with (x1, y1, x2, y2) for each pair
        # Pad with sentinel values (-1, -1, -1, -1) to mark end of array
        shader_swap_pairs = []
        for i, (x1, y1, x2, y2) in enumerate(self.swap_pairs):
            if i >= 16:  # Max 16 swap pairs in shader
                break
            shader_swap_pairs.append((x1, y1, x2, y2))
        
        # Pad to 16 elements with sentinel values
        while len(shader_swap_pairs) < 16:
            shader_swap_pairs.append((-1, -1, -1, -1))
        
        uniforms: IkedGridUniforms = {
            'u_time': t,
            'u_resolution': (self.width, self.height),
            'u_grid_size': self.grid_size,
            'u_swap_frequency': self.swap_frequency,
            'u_swap_phase': self.swap_phase,
            # 'u_swap_pairs': shader_swap_pairs,
            'tex0': self.upstream_tex,
        }
        return {
            'frag_shader_path': self.frag_shader_path,
            'uniforms': uniforms,
        }
    
    def render_texture(self, ctx: moderngl.Context, width: int, height: int, t: float) -> moderngl.Texture:
        self.upstream_tex = self.upstream_module.render_texture(ctx, width, height, t);

        # Render the module to a texture
        return super().render_texture(ctx, width, height, t)

if __name__ == "__main__":
    # Test with some interesting swap patterns
    swap_pairs = [
        (0, 0, 7, 7),      # Corner swap
        (1, 1, 6, 6),      # Inner corner swap
        (3, 3, 4, 4),      # Center swap
        (0, 3, 7, 4),      # Vertical edge swap
        (3, 0, 4, 7),      # Horizontal edge swap
    ]
    
    params = IkedGridParams(
        width=800, 
        height=600, 
        grid_size=8,
        swap_pairs=swap_pairs,
        swap_frequency=2.0,
        swap_phase=0.0
    )