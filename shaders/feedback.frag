#version 330
/*
feedback.frag
Description: Blends the current input texture with the previous frame for feedback effects (e.g. trails, motion blur).
Author: Oblique AI Agent
Inputs:
    - uniform float u_time; // Animation time in seconds
    - uniform vec2 u_resolution; // Viewport resolution
    - uniform float u_feedback_strength; // How much previous frame to blend (0.0 to 1.0)
    - uniform sampler2D u_feedback_texture; // Previous frame texture
    - uniform sampler2D u_input_texture; // Current input texture
*/

#ifdef GL_ES
precision mediump float;
#endif

uniform float u_time;
uniform vec2 u_resolution;
uniform float u_feedback_strength;
uniform sampler2D u_feedback_texture;
uniform sampler2D u_input_texture;

in vec2 v_uv;
out vec4 fragColor;

void main() {
    vec2 uv = v_uv;

    // Sample the current input
    vec4 current = texture(u_input_texture, uv);
    
    // Sample the previous frame
    vec4 previous = texture(u_feedback_texture, uv);

    // Additive feedback blending
    vec4 result = current + previous * u_feedback_strength;
    result = clamp(result, 0.0, 1.0);

    // Note: Removing clamp allows infinite accumulation when feedback_strength = 1.0

    fragColor = result;
} 