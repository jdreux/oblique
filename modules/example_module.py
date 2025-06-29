"""
Example Module - Demonstrates the dataclass-based uniform system.
This shows how to create a new module with type-safe uniforms.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
import moderngl
import numpy as np
from core.base_module import BaseAVModule, BaseUniforms


@dataclass
class ExampleUniforms(BaseUniforms):
    """Uniforms for the example shader.
    
    This dataclass defines exactly what uniforms the shader must have.
    The types and names must match the GLSL shader declarations.
    """
    # Basic parameters
    scale: float = 1.0
    rotation: float = 0.0
    
    # Colors
    primary_color: tuple[float, float, float] = (1.0, 0.0, 0.0)
    secondary_color: tuple[float, float, float] = (0.0, 0.0, 1.0)
    
    # Audio reactivity
    audio_intensity: float = 0.0
    audio_frequency: float = 0.0


class ExampleModule(BaseAVModule):
    """Example module demonstrating the dataclass uniform system."""
    
    def get_metadata(self) -> Dict[str, Any]:
        return {
            'name': 'ExampleModule',
            'description': 'Example module with dataclass uniforms',
            'parameters': {
                'scale': (float, 1.0, 0.1, 5.0),
                'rotation_speed': (float, 1.0, 0.0, 10.0),
                'primary_color': (tuple, (1.0, 0.0, 0.0), None, None),
                'secondary_color': (tuple, (0.0, 0.0, 1.0), None, None),
            },
            'shader_file': 'example.frag',  # You would create this shader
            'category': 'example'
        }
    
    def get_uniforms_class(self):
        """Return the uniform dataclass for this module."""
        return ExampleUniforms
    
    def setup(self, ctx: moderngl.Context):
        """Setup the module with OpenGL context."""
        super().setup(ctx)
        
        # Create full-screen quad for rendering
        quad_data = np.array([
            # positions     # texcoords
            -1.0, -1.0,     0.0, 0.0,
             1.0, -1.0,     1.0, 0.0,
             1.0,  1.0,     1.0, 1.0,
            -1.0,  1.0,     0.0, 1.0,
        ], dtype=np.float32)
        
        self.quad = ctx.buffer(quad_data.tobytes())
        self.vao = ctx.vertex_array(
            self.program,
            [(self.quad, '2f 2f', 'in_position', 'in_texcoord_0')]
        )
        
        # Create framebuffer
        texture = ctx.texture((ctx.viewport[2], ctx.viewport[3]), 4)
        texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.framebuffer = ctx.framebuffer(color_attachments=[texture])
    
    def update(self, processed_signals: Dict[str, Any], time_data: Dict[str, Any]):
        """Update module state based on processed signals and time data."""
        if not self.program or not self.ctx:
            return
        
        try:
            # Get parameters from props
            scale = self.props.get('scale', 1.0)
            rotation_speed = self.props.get('rotation_speed', 1.0)
            primary_color = self.props.get('primary_color', (1.0, 0.0, 0.0))
            secondary_color = self.props.get('secondary_color', (0.0, 0.0, 1.0))
            
            # Extract audio signals
            audio_signals = processed_signals.get('audio', {})
            envelope = audio_signals.get('envelope', 0.0)
            fft_bands = audio_signals.get('fft_bands', [])
            
            # Calculate audio frequency (simplified)
            audio_frequency = sum(fft_bands[8:16]) / 8 if len(fft_bands) >= 16 else 0.0
            
            # Calculate rotation
            rotation = time_data['time'] * rotation_speed
            
            # Update all uniforms using the dataclass system
            # This is type-safe and will catch any mismatches!
            self.update_uniforms(
                time=time_data['time'],
                resolution=(self.ctx.viewport[2], self.ctx.viewport[3]),
                scale=scale * (1.0 + envelope * 0.5),  # Audio-reactive scale
                rotation=rotation,
                primary_color=primary_color,
                secondary_color=secondary_color,
                audio_intensity=envelope,
                audio_frequency=audio_frequency
            )
            
        except Exception as e:
            print(f"Error updating uniforms: {e}")
    
    def render(self) -> Optional[moderngl.Framebuffer]:
        """Render the module to a framebuffer."""
        if not self.program or not self.vao or not self.framebuffer:
            return None
        
        self.framebuffer.use()
        self.ctx.clear(0.0, 0.0, 0.0, 1.0)
        self.vao.render(moderngl.TRIANGLE_FAN)
        return self.framebuffer
    
    def cleanup(self):
        """Clean up resources."""
        if hasattr(self, 'vao'):
            self.vao.release()
        if hasattr(self, 'quad'):
            self.quad.release()
        if hasattr(self, 'framebuffer') and self.framebuffer:
            self.framebuffer.release()
        super().cleanup()


# Example of how to use this module:
if __name__ == "__main__":
    from core.engine import ObliqueEngine
    
    engine = ObliqueEngine(800, 600, "Example Module Test")
    engine.initialize()
    
    module = ExampleModule({
        'scale': 1.5,
        'rotation_speed': 2.0,
        'primary_color': (0.2, 0.8, 0.2),
        'secondary_color': (0.8, 0.2, 0.8),
    })
    
    engine.add_module(module)
    engine.run() 