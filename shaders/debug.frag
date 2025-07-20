#version 330
/*
Debug shader for Oblique
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
in vec2 v_uv;

void main() {
    vec2 uv = v_uv;
    // Simple color: number modulates red, text not shown in MVP
    // fragColor = vec4(u_number, uv.x, uv.y, 1.0);
    // Render a simple grid of white squares on a black background for debug.
    // Each square is 0.1 x 0.1 in UV space, spaced in a 5x5 grid.
    vec2 grid = floor(v_uv * 5.0);
    vec2 cell_uv = fract(v_uv * 5.0);

    // Draw a filled square in each cell if inside 0.2 x 0.2 region
    float square = step(0.2, cell_uv.x) * step(0.2, cell_uv.y); // 0 outside, 1 inside

    // Color gradient based on UV coordinates (simple rainbow)
    vec3 gradient_color = vec3(v_uv.x, v_uv.y, 1.0 - v_uv.x);

    // Only show gradient inside the squares, black outside
    fragColor = vec4(gradient_color * square, 1.0);
} 