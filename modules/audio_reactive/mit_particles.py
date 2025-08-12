from dataclasses import dataclass

from modules.core.base_av_module import (
    BaseAVModule,
    BaseAVParams,
    OffscreenTexturePass,
    ParamFloat,
    ParamInt,
    Uniforms,
)


@dataclass
class MITParticlesParams(BaseAVParams):
    """Parameters for the MIT Particles module."""
    num_particles: ParamInt = 1000
    circle_radius: ParamFloat = 200.0
    gravity_strength: ParamFloat = 50.0
    swirl_strength: ParamFloat = 30.0
    noise_strength: ParamFloat = 20.0
    particle_size: ParamFloat = 2.0


class MITParticlesUniforms(Uniforms, total=True):
    u_time: float
    u_audio: float
    u_state: OffscreenTexturePass
    u_num_particles: int


class MITParticlesModule(BaseAVModule[MITParticlesParams, MITParticlesUniforms]):
    """
    MIT Particles module that renders a cloud of white particles that gravitate toward 
    and circulate along a circle. State is stored in a floating-point texture and updated 
    each frame via a ping-pong pass. Final pass renders point sprites.

    Features:
    - Particle physics simulation with gravity and circulation
    - Ping-pong texture updates for state management
    - Audio-reactive swirl and noise intensity
    - GPU-accelerated particle rendering
    - Configurable particle count and behavior parameters
    """

    metadata = {
        "name": "MITParticlesModule",
        "description": "Renders a cloud of white particles that gravitate toward and circulate along a circle with audio-reactive behavior.",
        "parameters": {
            "num_particles": "int",
            "circle_radius": "float",
            "gravity_strength": "float",
            "swirl_strength": "float",
            "noise_strength": "float",
            "particle_size": "float",
        },
    }
    frag_shader_path = "modules/audio_reactive/shaders/mit-particles.frag"

    # State update pass - updates particle positions and velocities
    # Note: ping_pong is currently a placeholder in the base class
    # We'll implement proper ping-pong behavior in the render_texture method
    state_update_pass: OffscreenTexturePass = OffscreenTexturePass(
        frag_shader_path="modules/audio_reactive/shaders/mit-particles-state.frag",
        uniforms={
            "u_resolution": (100,100),
            "u_center": (50,50),
            "u_radius": 50,
            "u_dt": 1.0 / 60.0,  # Assuming 60 FPS
            "u_time": 0,
            "u_audio": 1.0,  # This will be updated by the audio system
        }
    )

    def __init__(self, params: MITParticlesParams):
        super().__init__(params)

    def prepare_uniforms(self, t: float) -> MITParticlesUniforms:
        """
        Return uniforms for rendering.

        Args:
            t (float): Current time in seconds

        Returns:
            Uniforms: Uniform values to pass to the shader
        """
        resolution = self._resolve_resolution()

        return MITParticlesUniforms(
            u_resolution=resolution,
            u_time=t,
            u_audio=1.0,  # This will be updated by the audio system
            u_state=self.state_update_pass,
            u_num_particles=self._resolve_param(self.params.num_particles),
        )