#version 330
/*
Barrel/Pincushion Distortion shader for Oblique
Author: AI/Oblique
Description: Applies radial distortion to UV coordinates using barrel/pincushion effect
Inputs:
  uniform float u_strength; // Distortion strength (positive = barrel, negative = pincushion)
  uniform vec2 u_center; // Center point for distortion (0-1 UV space)
  uniform vec2 u_resolution; // Viewport resolution
  uniform float u_time; // Current time
  uniform sampler2D u_texture; // Input texture
*/

#ifdef GL_ES
precision mediump float;
#endif

uniform float u_strength;
uniform vec2 u_center;
uniform vec2 u_resolution;
uniform float u_time;
uniform sampler2D u_texture;

out vec4 fragColor;
in vec2 v_uv;

vec2 barrelPincushion(vec2 uv, float strength) {
    vec2 st = uv - 0.5;
    float radius = 1.0 + strength * dot(st, st);
    return 0.5 + radius * st;
}

void main() {
    // Apply barrel/pincushion distortion
    vec2 distorted_uv = barrelPincushion(v_uv, u_strength);
    
    // Sample the texture with distorted coordinates
    fragColor = texture(u_texture, distorted_uv);
} 