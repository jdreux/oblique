from dataclasses import dataclass
from typing import Any, Tuple
from modules.base_av_module import BaseAVModule, Uniforms, BaseAVParams

@dataclass
class CircleEchoParams(BaseAVParams):
    n_circles: int = 8
    n_points: int = 256
    mod_depth: float = 0.08
    echo_decay: float = 0.9
    max_echoes: int = 8
    # Placeholder for future audio features
    audio_level: float = 0.0
    band_amps: Tuple[float, ...] = (0.0,) * 16

class CircleEchoUniforms(Uniforms, total=True):
    u_time: float
    u_resolution: Tuple[int, int]
    u_n_circles: int
    u_n_points: int
    u_mod_depth: float
    u_echo_decay: float
    u_max_echoes: int
    # Placeholder uniforms for audio features
    u_audio_level: float
    u_band_amps: Tuple[float, ...]

class CircleEcho(BaseAVModule):
    """
    CircleEcho - Concentric modulated circles with echo/fade effect. Placeholder uniforms for future audio features.
    """
    metadata = {
        'name': 'CircleEcho',
        'description': 'Concentric modulated circles with echo/fade. Placeholder uniforms for future audio features.',
        'parameters': CircleEchoParams.__annotations__,
    }
    frag_shader_path: str = 'shaders/circle-echo.frag'

    def __init__(self, params: CircleEchoParams = CircleEchoParams()):
        super().__init__(params)
        self.width = self.params.width
        self.height = self.params.height
        self.n_circles = self.params.n_circles
        self.n_points = self.params.n_points
        self.mod_depth = self.params.mod_depth
        self.echo_decay = self.params.echo_decay
        self.max_echoes = self.params.max_echoes
        self.audio_level = self.params.audio_level
        self.band_amps = self.params.band_amps

    def update(self, params: CircleEchoParams):
        self.params = params
        self.width = self.params.width
        self.height = self.params.height
        self.n_circles = self.params.n_circles
        self.n_points = self.params.n_points
        self.mod_depth = self.params.mod_depth
        self.echo_decay = self.params.echo_decay
        self.max_echoes = self.params.max_echoes
        self.audio_level = self.params.audio_level
        self.band_amps = self.params.band_amps

    def render(self, t: float) -> dict[str, Any]:
        uniforms: CircleEchoUniforms = {
            'u_time': t,
            'u_resolution': (self.width, self.height),
            'u_n_circles': self.n_circles,
            'u_n_points': self.n_points,
            'u_mod_depth': self.mod_depth,
            'u_echo_decay': self.echo_decay,
            'u_max_echoes': self.max_echoes,
            'u_audio_level': self.audio_level,
            'u_band_amps': self.band_amps,
        }
        return {
            'frag_shader_path': self.frag_shader_path,
            'uniforms': uniforms,
        }

if __name__ == "__main__":
    params = CircleEchoParams(width=800, height=600, n_circles=8, n_points=256, mod_depth=0.08, echo_decay=0.9, max_echoes=8)
    module = CircleEcho(params)
    module.update(params)
    print(module.render(0.0)) 