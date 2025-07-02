from dataclasses import dataclass
from typing import Any, Tuple
from modules.base_av_module import BaseAVModule, Uniforms, BaseAVParams

@dataclass
class PauricParticlesParams(BaseAVParams):
    num_particles: int = 2**8;
    spread: float = 0.9  # 0.0 to 1.0, controls how wide the particles spread
    speed: float = 1.0   # Particle speed multiplier

class PauricParticlesUniforms(Uniforms, total=True):
    u_time: float
    u_resolution: Tuple[int, int]
    u_num_particles: int
    u_spread: float
    u_speed: float

class PauricParticles(BaseAVModule):
    """
    PauricParticles - Animated sprinkle of particles emanating from one corner and spreading across the screen.
    """
    metadata = {
        'name': 'PauricParticles',
        'description': 'Animated sprinkle of particles emanating from one corner and spreading across the screen.',
        'parameters': PauricParticlesParams.__annotations__,
    }
    frag_shader_path: str = 'shaders/pauric-particles.frag'

    def __init__(self, params: PauricParticlesParams = PauricParticlesParams()):
        super().__init__(params)
        self.width = self.params.width
        self.height = self.params.height
        self.num_particles = self.params.num_particles
        self.spread = self.params.spread
        self.speed = self.params.speed

    def update(self, params: PauricParticlesParams):
        self.params = params
        self.width = self.params.width
        self.height = self.params.height
        self.num_particles = self.params.num_particles
        self.spread = self.params.spread
        self.speed = self.params.speed

    def render(self, t: float) -> dict[str, Any]:
        uniforms: PauricParticlesUniforms = {
            'u_time': t,
            'u_resolution': (self.width, self.height),
            'u_num_particles': self.num_particles,
            'u_spread': self.spread,
            'u_speed': self.speed,
        }
        return {
            'frag_shader_path': self.frag_shader_path,
            'uniforms': uniforms,
        }

if __name__ == "__main__":
    params = PauricParticlesParams(width=800, height=600, num_particles=128, spread=0.5, speed=1.0)
    module = PauricParticles(params)
    module.update(params)
    print(module.render(0.0)) 