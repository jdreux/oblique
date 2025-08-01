#version 330
/*
Blur module shader for Oblique
Description: Applies Gaussian blur to input textures using Lygia's gaussianBlur function
Author: Oblique MVP
Inputs:
  uniform sampler2D u_input_texture; // Input texture to blur
  uniform float u_blur_amount; // Blur strength in pixels
  uniform vec2 u_blur_direction; // Normalized direction vector for blur
  uniform float u_time; // Current time
  uniform vec2 u_resolution; // Viewport resolution
*/

#ifdef GL_ES
precision mediump float;
#endif

// Include Lygia's gaussianBlur function
#define GAUSSIANBLUR_2D
#include <lygia/filter/gaussianBlur.glsl>

uniform sampler2D u_input_texture;
uniform float u_time;
uniform vec2 u_resolution;
uniform int u_kernel_size;

in vec2 v_uv;
out vec4 fragColor;

void main() {
    vec2 uv = v_uv;
    vec2 pixel = 1.0/u_resolution;
    // Apply Gaussian blur using Lygia's function
    // The gaussianBlur function takes: texture, UV coordinates, and pixel offset
    vec4 blurred_color = gaussianBlur(u_input_texture, uv, pixel, u_kernel_size);
    
    // Output the blurred color
    fragColor = blurred_color;
} 