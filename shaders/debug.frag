#version 330
/*
Debug shader for Oblique
Author: AI/Oblique
Inputs:
  uniform float u_number; // Number to display
  uniform sampler2D u_font; // Font texture atlas (optional, for text rendering)
  uniform vec2 u_resolution; // Viewport resolution
  // Text string is passed via uniform array or texture (MVP: hardcoded)
*/

#ifdef GL_ES
precision mediump float;
#endif

uniform float u_number;
uniform vec2 u_resolution;
// MVP: text string is not handled in shader, just color based on number

// 'fragColor' is the output variable for the fragment shader.
// It represents the final color of each pixel (fragment) drawn to the screen.
// 'vec4' is a GLSL vector type with 4 components: (red, green, blue, alpha).
// For example, vec4(1.0, 0.0, 0.0, 1.0) is opaque red.
// The shader writes the computed color to 'fragColor' for each pixel.
out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    // Simple color: number modulates red, text not shown in MVP
    // fragColor = vec4(u_number, uv.x, uv.y, 1.0);
    fragColor = vec4(gl_FragCoord.x / u_resolution.x, gl_FragCoord.y / u_resolution.y, u_number, 1.0);
    // TODO: Text rendering can be added with a font atlas and SDF in future
} 