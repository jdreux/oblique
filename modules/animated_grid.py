"""
Animated Grid Module
A simple animated grid pattern for testing the Oblique engine.
"""

import moderngl
import numpy as np
from typing import Dict, Any, Optional
from dataclasses import dataclass
from core.base_module import BaseAVModule, BaseUniforms


@dataclass
class AnimatedGridUniforms(BaseUniforms):
    """Uniforms for the animated grid shader."""
    grid_size: float = 20.0
    animation_speed: float = 1.0
    line_width: float = 0.02
    color: tuple[float, float, float] = (0.8, 0.2, 0.8)
    audio_intensity: float = 0.0
    audio_envelope: float = 0.0
    audio_peak: float = 0.0


class AnimatedGrid(BaseAVModule):
    """Simple animated grid pattern module."""
    
    def get_metadata(self) -> Dict[str, Any]:
        return {
            'name': 'AnimatedGrid',
            'description': 'Audio-reactive animated grid pattern',
            'parameters': {
                'grid_size': (float, 20.0, 1.0, 100.0),
                'animation_speed': (float, 1.0, 0.1, 5.0),
                'line_width': (float, 0.02, 0.001, 0.1),
                'color': (tuple, (0.8, 0.2, 0.8), None, None),
                'audio_sensitivity': (float, 2.0, 0.1, 10.0),
                'base_intensity': (float, 0.3, 0.0, 1.0)
            },
            'shader_file': 'animated-grid.frag',
            'category': 'pattern'
        }
    
    def get_uniforms_class(self):
        """Return the uniform dataclass for this module."""
        return AnimatedGridUniforms
    
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
        
        # Create vertex array object
        self.vao = ctx.vertex_array(
            self.program,
            [
                (self.quad, '2f 2f', 'in_position', 'in_texcoord_0'),
            ]
        )
        
        # Create framebuffer for rendering
        self.framebuffer = self._create_framebuffer()
    
    def _create_framebuffer(self) -> Optional[moderngl.Framebuffer]:
        """Create a framebuffer for this module."""
        if not self.ctx:
            return None
        texture = self.ctx.texture((self.ctx.viewport[2], self.ctx.viewport[3]), 4)
        texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
        return self.ctx.framebuffer(color_attachments=[texture])
    
    def update(self, processed_signals: Dict[str, Any], time_data: Dict[str, Any]):
        """Update module state based on processed signals and time data."""
        if not self.program or not self.ctx:
            print("❌ No program or context available")
            return
            
        try:
            # Get parameters from props
            grid_size = self.props.get('grid_size', 20.0)
            animation_speed = self.props.get('animation_speed', 1.0)
            line_width = self.props.get('line_width', 0.02)
            color = self.props.get('color', (0.8, 0.2, 0.8))
            audio_sensitivity = self.props.get('audio_sensitivity', 2.0)
            base_intensity = self.props.get('base_intensity', 0.3)
            
            # Extract processed audio signals
            audio_signals = processed_signals.get('audio', {})
            envelope = audio_signals.get('envelope', 0.0)
            peak = audio_signals.get('peak', 0.0)
            
            # Extract events
            events = processed_signals.get('events', {})
            beat = events.get('beat', False)
            
            # Make grid reactive to audio
            audio_intensity = (envelope * 0.7 + peak * 0.3) * audio_sensitivity
            audio_intensity = min(audio_intensity, 1.0)  # Clamp to 0-1
            
            # Boost intensity on beats
            if beat:
                audio_intensity = min(audio_intensity * 1.5, 1.0)
            
            # Adjust animation speed based on audio
            dynamic_speed = animation_speed * (1.0 + audio_intensity * 2.0)
            
            # Adjust line width based on audio
            dynamic_line_width = line_width * (1.0 + audio_intensity * 0.5)
            
            # Adjust grid size based on audio (more dynamic when loud)
            dynamic_grid_size = grid_size * (1.0 - audio_intensity * 0.3)
            
            # Calculate final intensity
            final_intensity = base_intensity + audio_intensity * (1.0 - base_intensity)
            
            # Update all uniforms using the dataclass system
            print(f"🎨 Setting uniforms: time={time_data['time']:.2f}, intensity={final_intensity:.2f}")
            self.update_uniforms(
                time=time_data['time'],
                resolution=(self.ctx.viewport[2], self.ctx.viewport[3]),
                grid_size=dynamic_grid_size,
                animation_speed=dynamic_speed,
                line_width=dynamic_line_width,
                color=color,
                audio_intensity=final_intensity,
                audio_envelope=envelope,
                audio_peak=peak
            )
            
        except Exception as e:
            print(f"❌ Error updating uniforms: {e}")
    
    def render(self) -> Optional[moderngl.Framebuffer]:
        """Render the animated grid to a framebuffer."""
        if not self.program or not self.vao or not self.framebuffer or not self.ctx:
            print("❌ Missing components for rendering")
            return None
        
        try:
            # Bind framebuffer
            self.framebuffer.use()
            
            # Clear framebuffer
            self.ctx.clear(0.0, 0.0, 0.0, 1.0)
            
            # Render to framebuffer
            self.vao.render(moderngl.TRIANGLE_FAN)
            
            print("✅ Rendered successfully")
            return self.framebuffer
            
        except Exception as e:
            print(f"❌ Error during rendering: {e}")
            return None
    
    def cleanup(self):
        """Clean up resources."""
        if hasattr(self, 'vao'):
            self.vao.release()
        if hasattr(self, 'quad'):
            self.quad.release()
        if hasattr(self, 'framebuffer') and self.framebuffer:
            self.framebuffer.release()
        super().cleanup()


if __name__ == "__main__":
    # Test the module
    from core.engine import ObliqueEngine
    
    engine = ObliqueEngine(390, 844, "Animated Grid Test")
    engine.initialize()
    
    module = AnimatedGrid({
        'grid_size': 15.0,
        'animation_speed': 2.0,
        'line_width': 0.03,
        'color': (0.2, 0.8, 0.8),
        'audio_sensitivity': 3.0,
        'base_intensity': 0.2
    })
    
    engine.add_module(module)
    engine.run() 