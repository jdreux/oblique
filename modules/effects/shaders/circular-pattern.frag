#version 330
/*
Circular Pattern shader for Oblique
Author: Oblique MVP
Description: Generates concentric circular lines with per-segment noise distortion.
Inputs:
  uniform float u_time;            // Current time
  uniform vec2 u_resolution;       // Viewport resolution
  uniform float u_ring_count;      // Number of concentric rings
  uniform int u_segment_count;     // Number of angular segments
  uniform float u_line_width;      // Thickness of ring lines
  uniform float u_noise_amplitude; // Amount of radial noise
  uniform float u_speed;           // Animation speed
*/

#ifdef GL_ES
precision mediump float;
#endif

#include <lygia/space/cart2polar.glsl>
#include <lygia/generative/snoise.glsl>

uniform float u_time;
uniform vec2 u_resolution;
uniform float u_ring_count;
uniform int u_segment_count;
uniform float u_line_width;
uniform float u_noise_amplitude;
uniform float u_speed;

in vec2 v_uv;
out vec4 fragColor;

void main() {
    vec2 uv = v_uv;
    vec2 centered = (uv - 0.5) * 2.0;
    vec2 polar = cart2polar(centered);
    float angle = polar.x;
    float radius = polar.y;

    float segment = floor((angle + 3.14159265) / (2.0 * 3.14159265)
                          * float(u_segment_count));
    float base = radius * u_ring_count;
    float n = snoise(vec2(segment, floor(base)) + u_time * u_speed);
    float displaced = base + n * u_noise_amplitude;
    float ring = fract(displaced);
    float line = step(u_line_width, ring);

    float color = 1.0 - line;
    fragColor = vec4(vec3(color), 1.0);
}
