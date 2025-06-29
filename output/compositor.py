"""
Compositor for Oblique.
Blends and composes module framebuffers into a final image.
"""

import moderngl
import numpy as np
from typing import Dict, List, Any, Optional
from core.base_module import BaseAVModule


class Compositor:
    """Compose multiple module outputs into a final image."""
    
    def __init__(self, ctx: moderngl.Context, width: int, height: int):
        """Initialize the compositor."""
        self.ctx = ctx
        self.width = width
        self.height = height
        self.modules = []
        self.composition_mode = 'blend'  # 'blend', 'add', 'multiply', 'overlay'
        
        # Create composition shader
        self.composition_program = self._create_composition_shader()
        
        # Create full-screen quad for composition
        quad_data = np.array([
            # positions     # texcoords
            -1.0, -1.0,     0.0, 0.0,
             1.0, -1.0,     1.0, 0.0,
             1.0,  1.0,     1.0, 1.0,
            -1.0,  1.0,     0.0, 1.0,
        ], dtype=np.float32)
        self.quad = self.ctx.buffer(quad_data.tobytes())
        
        # Create vertex array for composition
        self.vao = self.ctx.vertex_array(
            self.composition_program,
            [(self.quad, '2f 2f', 'in_position', 'in_texcoord_0')]
        )
    
    def add_module(self, module: BaseAVModule):
        """Add a module to the composition."""
        self.modules.append(module)
    
    def remove_module(self, module: BaseAVModule):
        """Remove a module from the composition."""
        if module in self.modules:
            self.modules.remove(module)
    
    def set_composition_mode(self, mode: str):
        """Set the composition mode."""
        valid_modes = ['blend', 'add', 'multiply', 'overlay']
        if mode in valid_modes:
            self.composition_mode = mode
    
    def compose(self, processed_signals: Dict[str, Any], time_data: Dict[str, Any]) -> moderngl.Framebuffer:
        """Compose all active modules into a final framebuffer."""
        if not self.modules:
            # Return empty framebuffer if no modules
            return self._create_empty_framebuffer()
        
        # Update and render all modules
        module_outputs = []
        for module in self.modules:
            module.update(processed_signals, time_data)
            output = module.render()
            if output:
                module_outputs.append(output)
        
        if not module_outputs:
            return self._create_empty_framebuffer()
        
        # Compose module outputs
        if len(module_outputs) == 1:
            return module_outputs[0]
        else:
            return self._blend_framebuffers(module_outputs)
    
    def _create_empty_framebuffer(self) -> moderngl.Framebuffer:
        """Create an empty framebuffer."""
        texture = self.ctx.texture((self.width, self.height), 4)
        texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
        return self.ctx.framebuffer(color_attachments=[texture])
    
    def _blend_framebuffers(self, framebuffers: List[moderngl.Framebuffer]) -> moderngl.Framebuffer:
        """Blend multiple framebuffers together."""
        if not framebuffers:
            return self._create_empty_framebuffer()
        
        # Create output framebuffer
        output_texture = self.ctx.texture((self.width, self.height), 4)
        output_texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
        output_framebuffer = self.ctx.framebuffer(color_attachments=[output_texture])
        
        # Bind output framebuffer
        output_framebuffer.use()
        
        # Blend framebuffers based on composition mode
        if self.composition_mode == 'blend':
            self._blend_mode(framebuffers)
        elif self.composition_mode == 'add':
            self._add_mode(framebuffers)
        elif self.composition_mode == 'multiply':
            self._multiply_mode(framebuffers)
        elif self.composition_mode == 'overlay':
            self._overlay_mode(framebuffers)
        
        return output_framebuffer
    
    def _blend_mode(self, framebuffers: List[moderngl.Framebuffer]):
        """Blend mode composition."""
        # Simple alpha blending
        for i, fb in enumerate(framebuffers):
            alpha = 1.0 / len(framebuffers)  # Equal weight for each module
            self._render_framebuffer(fb, alpha)
    
    def _add_mode(self, framebuffers: List[moderngl.Framebuffer]):
        """Additive composition."""
        for fb in framebuffers:
            self._render_framebuffer(fb, 1.0, blend_func='add')
    
    def _multiply_mode(self, framebuffers: List[moderngl.Framebuffer]):
        """Multiplicative composition."""
        for fb in framebuffers:
            self._render_framebuffer(fb, 1.0, blend_func='multiply')
    
    def _overlay_mode(self, framebuffers: List[moderngl.Framebuffer]):
        """Overlay composition."""
        for fb in framebuffers:
            self._render_framebuffer(fb, 1.0, blend_func='overlay')
    
    def _render_framebuffer(self, framebuffer: moderngl.Framebuffer, alpha: float, blend_func: str = 'normal'):
        """Render a framebuffer with specified blending."""
        # Set blending mode
        if blend_func == 'add':
            self.ctx.blend_func = moderngl.ONE, moderngl.ONE
        elif blend_func == 'multiply':
            self.ctx.blend_func = moderngl.DST_COLOR, moderngl.ZERO
        elif blend_func == 'overlay':
            self.ctx.blend_func = moderngl.ONE, moderngl.ONE_MINUS_SRC_ALPHA
        else:
            self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        
        # Bind framebuffer texture
        if framebuffer.color_attachments:
            texture = framebuffer.color_attachments[0]
            texture.use(0)
        
        # Render quad
        self.vao.render(moderngl.TRIANGLE_FAN)
    
    def _create_composition_shader(self) -> moderngl.Program:
        """Create the composition shader program."""
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
        
        fragment_shader = """
            #version 330
            uniform sampler2D texture0;
            in vec2 uv;
            out vec4 fragColor;
            void main() {
                fragColor = texture(texture0, uv);
            }
        """
        
        return self.ctx.program(
            vertex_shader=vertex_shader,
            fragment_shader=fragment_shader
        )
    
    def cleanup(self):
        """Clean up resources."""
        if self.vao:
            self.vao.release()
        if self.quad:
            self.quad.release()
        if self.composition_program:
            self.composition_program.release() 