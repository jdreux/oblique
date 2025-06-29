"""
Display for Oblique.
Handles window, Syphon, recording, and other output options.
"""

import moderngl
import glfw
import numpy as np
from typing import Dict, Any, Optional
import time


class Display:
    """Handle display output for Oblique."""
    
    def __init__(self, width: int = 390, height: int = 844, title: str = "Oblique"):
        """Initialize the display."""
        self.width = width
        self.height = height
        self.title = title
        self.window = None
        self.ctx = None
        self.output_mode = 'window'  # 'window', 'syphon', 'recording'
        
        # Recording settings
        self.recording = False
        self.recording_frames = []
        self.recording_fps = 60
        
        # Syphon settings (future)
        self.syphon_server = None
        
    def initialize(self):
        """Initialize GLFW and OpenGL context."""
        # Initialize GLFW
        if not glfw.init():
            raise RuntimeError("Failed to initialize GLFW")
        
        # Configure GLFW
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)
        
        # Create window
        self.window = glfw.create_window(self.width, self.height, self.title, None, None)
        if not self.window:
            glfw.terminate()
            raise RuntimeError("Failed to create GLFW window")
        
        glfw.make_context_current(self.window)
        
        # Initialize ModernGL context
        self.ctx = moderngl.create_context()
        
        print(f"Display initialized: {self.width}x{self.height}")
    
    def set_output_mode(self, mode: str):
        """Set the output mode."""
        valid_modes = ['window', 'syphon', 'recording']
        if mode in valid_modes:
            self.output_mode = mode
    
    def display_framebuffer(self, framebuffer: moderngl.Framebuffer):
        """Display a framebuffer based on the current output mode."""
        if not self.ctx or not self.window:
            return
        
        # Clear the screen
        self.ctx.clear(0.1, 0.1, 0.1, 1.0)
        
        if self.output_mode == 'window':
            self._display_to_window(framebuffer)
        elif self.output_mode == 'syphon':
            self._display_to_syphon(framebuffer)
        elif self.output_mode == 'recording':
            self._display_to_recording(framebuffer)
        
        # Swap buffers
        glfw.swap_buffers(self.window)
    
    def _display_to_window(self, framebuffer: moderngl.Framebuffer):
        """Display framebuffer to window."""
        # Bind the framebuffer texture
        if framebuffer.color_attachments:
            texture = framebuffer.color_attachments[0]
            texture.use(0)
        
        # Render full-screen quad
        self._render_fullscreen_quad()
    
    def _display_to_syphon(self, framebuffer: moderngl.Framebuffer):
        """Display framebuffer to Syphon (placeholder for future implementation)."""
        # For now, just display to window
        self._display_to_window(framebuffer)
        
        # TODO: Implement Syphon output
        # This would involve:
        # 1. Creating a Syphon server
        # 2. Converting framebuffer to image data
        # 3. Publishing to Syphon
    
    def _display_to_recording(self, framebuffer: moderngl.Framebuffer):
        """Display framebuffer to recording."""
        # Display to window as well
        self._display_to_window(framebuffer)
        
        # Capture frame for recording
        if self.recording:
            frame_data = self._capture_framebuffer(framebuffer)
            self.recording_frames.append(frame_data)
    
    def _render_fullscreen_quad(self):
        """Render a full-screen quad."""
        # Create simple quad data
        quad_data = np.array([
            # positions     # texcoords
            -1.0, -1.0,     0.0, 0.0,
             1.0, -1.0,     1.0, 0.0,
             1.0,  1.0,     1.0, 1.0,
            -1.0,  1.0,     0.0, 1.0,
        ], dtype=np.float32)
        
        # Create buffer and program
        quad_buffer = self.ctx.buffer(quad_data.tobytes())
        
        program = self.ctx.program(
            vertex_shader="""
                #version 330
                in vec2 in_position;
                in vec2 in_texcoord_0;
                out vec2 uv;
                void main() {
                    gl_Position = vec4(in_position, 0.0, 1.0);
                    uv = in_texcoord_0;
                }
            """,
            fragment_shader="""
                #version 330
                uniform sampler2D texture0;
                in vec2 uv;
                out vec4 fragColor;
                void main() {
                    fragColor = texture(texture0, uv);
                }
            """
        )
        
        # Create vertex array and render
        vao = self.ctx.vertex_array(
            program,
            [(quad_buffer, '2f 2f', 'in_position', 'in_texcoord_0')]
        )
        
        vao.render(moderngl.TRIANGLE_FAN)
        
        # Cleanup
        vao.release()
        quad_buffer.release()
        program.release()
    
    def _capture_framebuffer(self, framebuffer: moderngl.Framebuffer) -> np.ndarray:
        """Capture framebuffer data as numpy array."""
        # Read pixels from framebuffer
        pixels = framebuffer.read(components=4)
        
        # Convert to numpy array and reshape
        data = np.frombuffer(pixels, dtype=np.uint8)
        data = data.reshape(self.height, self.width, 4)
        
        return data
    
    def start_recording(self):
        """Start recording frames."""
        self.recording = True
        self.recording_frames = []
        print("Recording started")
    
    def stop_recording(self):
        """Stop recording frames."""
        self.recording = False
        print(f"Recording stopped. Captured {len(self.recording_frames)} frames")
    
    def save_recording(self, filename: str):
        """Save recorded frames to a video file."""
        if not self.recording_frames:
            print("No frames to save")
            return
        
        # TODO: Implement video saving using FFmpeg or similar
        # This would involve:
        # 1. Converting frames to video format
        # 2. Using FFmpeg to encode
        # 3. Saving to file
        
        print(f"Recording saved to {filename} (placeholder)")
    
    def should_close(self) -> bool:
        """Check if the window should close."""
        if not self.window:
            return True
        return glfw.window_should_close(self.window)
    
    def poll_events(self):
        """Poll GLFW events."""
        if self.window:
            glfw.poll_events()
    
    def cleanup(self):
        """Clean up display resources."""
        if self.window:
            glfw.destroy_window(self.window)
        glfw.terminate()
        print("Display cleaned up") 