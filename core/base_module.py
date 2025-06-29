"""
Base module interface for Oblique AV modules.
All visual modules must inherit from this class.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type, get_type_hints
from dataclasses import dataclass, fields
import moderngl


@dataclass
class BaseUniforms:
    """Base uniform dataclass that all modules should extend."""
    time: float = 0.0
    resolution: tuple[float, float] = (800.0, 600.0)


class BaseAVModule(ABC):
    """Base class for all audio-visual modules in Oblique."""
    
    def __init__(self, props: Optional[Dict[str, Any]] = None):
        """Initialize the module with optional properties."""
        self.props = props or {}
        self.metadata = self.get_metadata()
        self.ctx = None  # Will be set by engine
        self.program = None  # Shader program
        self.uniforms = self.create_uniforms()
        
    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """Return module metadata including name, description, and parameters."""
        return {
            'name': 'BaseModule',
            'description': 'Base class for AV modules',
            'parameters': {},
            'shader_file': None,
            'category': 'base'
        }
    
    def get_uniforms_class(self) -> Type[BaseUniforms]:
        """Return the dataclass that defines this module's uniforms.
        
        Override this method to return your custom uniform dataclass.
        The shader must declare uniforms that match this dataclass exactly.
        """
        return BaseUniforms
    
    def create_uniforms(self) -> BaseUniforms:
        """Create a uniform instance from the dataclass."""
        return self.get_uniforms_class()()
    
    def setup(self, ctx: moderngl.Context):
        """Setup the module with OpenGL context and load shader."""
        self.ctx = ctx
        shader_file = self.metadata.get('shader_file')
        if shader_file:
            self.program = self.load_shader(shader_file)
    
    def update_uniforms(self, **kwargs):
        """Update uniform values and set them in the shader."""
        if self.program is None:
            return
        
        # Update the uniform dataclass
        for key, value in kwargs.items():
            if hasattr(self.uniforms, key):
                setattr(self.uniforms, key, value)
        
        # Set all uniforms in the shader
        for field in fields(self.uniforms):
            try:
                value = getattr(self.uniforms, field.name)
                self.program[field.name] = value
            except Exception as e:
                print(f"❌ Error setting uniform '{field.name}': {e}")
                # Don't fail completely, just log the error
    
    def load_shader(self, shader_file: str) -> Optional[moderngl.Program]:
        """Load and compile the GLSL shader for this module."""
        try:
            with open(f"shaders/{shader_file}", 'r') as f:
                fragment_shader = f.read()
            
            # Create a simple vertex shader for full-screen quad
            vertex_shader = """
                #version 330
                in vec2 in_position;
                in vec2 in_texcoord_0;
                out vec2 uv;
                void main() {
                    gl_Position = vec4(in_position, 0.0, 1.0);
                    uv = in_texcoord_0;
                }
            """
            
            return self.ctx.program(
                vertex_shader=vertex_shader,
                fragment_shader=fragment_shader
            )
        except Exception as e:
            print(f"Error loading shader {shader_file}: {e}")
            return None
    
    def update(self, processed_signals: Dict[str, Any], time_data: Dict[str, Any]):
        """Update module state based on processed signals and time data.
        
        Args:
            processed_signals: Dictionary containing:
                - 'audio': Normalized audio features (fft_bands, envelope, peak, etc.)
                - 'midi': Normalized MIDI data (future)
                - 'osc': Normalized OSC data (future)
                - 'time': Normalized time data (time, time_cycle, delta_time)
                - 'combined': All signals combined for easy access
                - 'events': Detected events (beat, trigger, threshold_cross, etc.)
            time_data: Raw time data (time, delta_time, frame_count)
        """
        pass
    
    @abstractmethod
    def render(self) -> Optional[moderngl.Framebuffer]:
        """Render the module and return a framebuffer (or None for direct screen rendering)."""
        pass
    
    def cleanup(self):
        """Clean up resources when module is destroyed."""
        if self.program:
            self.program.release() 