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
uniform float u_time;
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

    // Animate the grid over time using u_number as a time uniform (MVP: no u_time, so use u_number)
    float t = u_number;

    // Animate grid position: make the grid "slide" diagonally over time
    vec2 animated_uv = uv + vec2(sin(t * 0.5), cos(t * 0.5)) * 0.1;

    // 5x5 grid
    vec2 grid = floor(animated_uv * 5.0);
    vec2 cell_uv = fract(animated_uv * 5.0);

    // Animate the size of the squares with a pulsating effect
    float pulse = 0.15 + 0.05 * sin(t * 2.0 + grid.x + grid.y);

    // Draw a filled square in each cell if inside pulse x pulse region
    float square = step(pulse, cell_uv.x) * step(pulse, cell_uv.y);

    // Color gradient based on animated UV coordinates (simple rainbow)
    vec3 gradient_color = vec3(animated_uv.x, animated_uv.y, 1.0 - animated_uv.x);

    // Only show gradient inside the squares, black outside
    fragColor = vec4(gradient_color * square, 1.0);
}