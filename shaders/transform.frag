#version 330
/*
Transform shader for Oblique
Author: AI/Oblique
Description: Applies affine transformations (scale, rotate, translate) to UV coordinates
Inputs:
  uniform mat3 u_transform_matrix; // 3x3 affine transformation matrix
  uniform vec2 u_resolution; // Viewport resolution
  uniform float u_time; // Current time
  uniform sampler2D u_texture; // Input texture 
*/

#ifdef GL_ES
precision mediump float;
#endif

uniform mat3 u_transform_matrix;
uniform vec2 u_resolution;
uniform float u_time;
uniform sampler2D u_texture;

out vec4 fragColor;
in vec2 v_uv;


void main() {
    
    vec3 homogeneous_uv = vec3(v_uv, 1.0);
    
    // Apply transformation matrix
    vec3 transformed = u_transform_matrix * homogeneous_uv;

    // Return 2D coordinates
    fragColor = texture(u_texture, transformed.xy);
}