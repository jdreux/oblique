#version 330 core
/*
BlueBackNGray Final Shader – Oblique
Applies vertical strips offset effect to circles texture.
Creates a staggered effect by shifting fragments up/down in vertical strips.

Author: AI Agent
Inputs: Circles texture, strip offset parameter

Uniforms
--------
  u_time            Seconds since start.
  u_resolution      Viewport in pixels.
  u_strip_offset    Pixel offset for vertical strips.
  u_circles_texture Texture containing the circles from background pass.
*/

#ifdef GL_ES
precision mediump float;
#endif

uniform float u_time;
uniform vec2 u_resolution;
uniform float u_strip_offset;
uniform sampler2D u_circles_texture;

out vec4 fragColor;
in vec2 v_uv;

// Use built-in GLSL functions for simplicity

/* ─── Visual Constants ──────────────────────────────────────────────────── */
const float STRIP_WIDTH = 40.0;          // Width of each vertical strip in pixels
const int HORIZONTAL_BREAKS = 6;         // Number of horizontal breaks per strip
const float BREAK_OFFSET_SCALE = 10;    // Scale factor for break offsets

/* ─── Main Shader ───────────────────────────────────────────────────────── */
void main()
{
    vec2 uv = v_uv;
    
    // Calculate which vertical strip we're in
    float x_pixel = uv.x * u_resolution.x;
    float strip_index = floor(x_pixel / STRIP_WIDTH);
    
    // Create alternating offset pattern for vertical strips
    float strip_offset_direction = mod(strip_index, 2.0) * 2.0 - 1.0;  // -1 or +1
    
    // Calculate which horizontal break we're in within this strip
    float y_pixel = uv.y * u_resolution.y;
    float break_height = u_resolution.y / float(HORIZONTAL_BREAKS);
    float break_index = floor(y_pixel / break_height);
    
    // Create pseudo-random offset for each break based on strip and break indices
    // Use a simple hash function to get different offsets for each break
    float hash_input = strip_index * 17.0 + break_index * 31.0;
    float break_offset_factor = fract(sin(hash_input) * 43758.5453) * 2.0 - 1.0;  // -1 to +1
    
    // Combine strip offset with break-specific offset
    float total_pixel_offset = strip_offset_direction * u_strip_offset + 
                               break_offset_factor * u_strip_offset * BREAK_OFFSET_SCALE;
    float total_uv_offset = total_pixel_offset / u_resolution.y;
    
    // Apply the combined offset to the UV coordinates
    vec2 offset_uv = uv;
    offset_uv.y += total_uv_offset;
    
    // Sample the circles texture with the offset
    vec4 circles_color = texture(u_circles_texture, offset_uv);
    
    fragColor = circles_color;
} 