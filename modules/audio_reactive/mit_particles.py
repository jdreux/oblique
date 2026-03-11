from dataclasses import dataclass, field

from core.registry import oblique_module
from modules.core.base_av_module import (
    BaseAVModule,
    BaseAVParams,
    ParamFloat,
    ParamInt,
    TexturePass,
    Uniforms,
)



@dataclass
class MITParticlesParams(BaseAVParams):
    """Parameters for the MIT Particles module.
    
    Performance note: This fragment shader approach has O(pixels × particles) complexity.
    For 800x600 resolution, each additional 100 particles adds ~48M operations per frame.
    Recommended ranges:
    - For 60fps: 50-200 particles
    - For 30fps: 200-500 particles  
    - For 15fps: 500-1000 particles
    """
    num_particles: ParamInt = field(
        default=200,
        metadata={
            "min": 1,
            "max": 2000,
            "description": "Number of simulated particles (higher values increase GPU cost).",
        },
    )
    circle_radius: ParamFloat = field(
        default=200.0,
        metadata={
            "min": 1.0,
            "max": 4000.0,
            "description": "Target radius of the particle orbit in pixels.",
        },
    )
    gravity_strength: ParamFloat = field(
        default=6.0,
        metadata={
            "min": 0.0,
            "max": 50.0,
            "description": "Radial spring force pulling particles toward the orbit.",
        },
    )
    swirl_strength: ParamFloat = field(
        default=140.0,
        metadata={
            "min": 0.0,
            "max": 800.0,
            "description": "Tangential swirl acceleration applied to particles.",
        },
    )
    noise_strength: ParamFloat = field(
        default=20.0,
        metadata={
            "min": 0.0,
            "max": 400.0,
            "description": "Random acceleration noise injected into particle motion.",
        },
    )
    particle_size: ParamFloat = field(
        default=3.0,
        metadata={
            "min": 0.1,
            "max": 24.0,
            "description": "Base rendered size of each particle in pixels.",
        },
    )




class MITParticlesUniforms(Uniforms, total=True):
    u_time: float
    u_audio: float
    u_state: TexturePass
    u_num_particles: int
    u_tex_size: tuple[int, int]
    u_point_size_px: float
    u_size_speed_scale: float
    u_softness: float
    u_exposure: float



@oblique_module(
    category="audio_reactive",
    description="Simulates and renders an audio-reactive particle field with ping-pong state.",
    tags=["particle", "audio-reactive", "chaotic", "evolving", "dense"],
    cost_hint="high",
)
class MITParticlesModule(BaseAVModule[MITParticlesParams, MITParticlesUniforms]):
    """
    MIT Particles module that renders a cloud of white particles that gravitate toward 
    and circulate along a circle. State is stored in a floating-point texture and updated 
    each frame via a ping-pong pass. Final pass renders point sprites.

    PERFORMANCE WARNING: This implementation has O(pixels × particles) complexity.
    Use fewer particles for higher frame rates. Consider switching to point sprite
    rendering or instanced geometry for better performance with large particle counts.

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
    particle_state_texture: TexturePass = TexturePass(
        frag_shader_path="modules/audio_reactive/shaders/mit-particles-state.frag",
        uniforms={
            "u_tex_size": (100, 100),
            "u_num_particles": 200,
            "u_resolution": (100, 100),
            "u_center": (50, 50),
            "u_radius": 50,
            "u_dt": 1.0 / 60.0,  # Assuming 60 FPS
            # dynamics (overridden per-frame)
            "u_gravity_strength": 6.0,
            "u_swirl_strength": 140.0,
            "u_noise_strength": 20.0,
        },
        ping_pong=True,
        previous_uniform_name="u_state_prev",
    )

    def __init__(self, params: MITParticlesParams):
        super().__init__(params)

    def _compute_state_grid(self, num_particles: int) -> tuple[int, int]:
        """Compute a near-square grid size that can contain num_particles texels."""
        if num_particles <= 0:
            return (1, 1)
        import math
        w = int(math.ceil(math.sqrt(num_particles)))
        h = int(math.ceil(num_particles / w))
        return (w, h)

    def prepare_uniforms(self, t: float) -> MITParticlesUniforms:
        """
        Return uniforms for rendering.

        Args:
            t (float): Current time in seconds

        Returns:
            Uniforms: Uniform values to pass to the shader
        """
        resolution = self._resolve_resolution()

        # Resolve dynamic parameters
        num_particles = self._resolve_param(self.params.num_particles)
        tex_w, tex_h = self._compute_state_grid(num_particles)
        center = (self._resolve_param(self.params.width) / 2, self._resolve_param(self.params.height) / 2)
        radius = self._resolve_param(self.params.circle_radius)
        gravity = self._resolve_param(self.params.gravity_strength)
        swirl = self._resolve_param(self.params.swirl_strength)
        noise = self._resolve_param(self.params.noise_strength)

        # Keep the state texture sized to the particle grid, not the framebuffer
        self.particle_state_texture.width = tex_w
        self.particle_state_texture.height = tex_h

        # Update per-frame uniforms for the state pass (these override static defaults)
        self.particle_state_texture.uniforms.update({
            "u_tex_size": (tex_w, tex_h),
            "u_num_particles": num_particles,
            "u_resolution": (tex_w, tex_h),
            "u_center": center,
            "u_radius": radius,
            "u_dt": 1.0 / 60.0,
            "u_time": t,
            "u_audio": radius,
            "u_gravity_strength": gravity,
            "u_swirl_strength": swirl,
            "u_noise_strength": noise,
        })

        return MITParticlesUniforms(
            u_resolution=resolution,
            u_time=t,
            u_audio=1.0,
            u_num_particles=num_particles,
            u_state=self.particle_state_texture,
            u_tex_size=(tex_w, tex_h),
            u_point_size_px=float(self._resolve_param(self.params.particle_size)),
            u_size_speed_scale=1.0,
            u_softness=1.0,
            u_exposure=1.0,
        )
