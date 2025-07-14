#version 330
/*
Ikeda Tiny Barcode Pattern Shader for Oblique
Author: AI/Oblique (adapted from ShaderToy https://www.shadertoy.com/view/XtdcWS)
Description: Generates a glitchy barcode pattern inspired by Ikeda's work
Inputs:
  uniform vec2 u_resolution; // Viewport resolution
  uniform float u_time; // Current time for animation
  uniform float u_pattern_intensity; // Pattern intensity multiplier
  uniform float u_barcode_width; // Width of barcode elements
  uniform float u_noise_scale; // Scale of noise pattern
  uniform float u_threshold; // Threshold for pattern generation
  uniform sampler2D tex0; // Input texture (optional)
*/

#ifdef GL_ES
precision mediump float;
#endif

uniform vec2 u_resolution;
uniform float u_time;
uniform float u_pattern_intensity;
uniform float u_barcode_width;
uniform float u_noise_scale;
uniform float u_threshold;
uniform sampler2D tex0;
uniform float u_fft_bands[512];

out vec4 fragColor;
in vec2 v_uv;

// Noise function adapted from Shadertoy implementation
float N(vec2 u) {
    return fract(sin(dot(floor(u * u_noise_scale), vec2(12.13, 4.47))) * 13.5 + u_time);
}

void main() {

    // vec2 f = v_uv * u_resolution;   
    // vec2 u= f/u_resolution.y;
    // u.y-=mod(u.y,1./128.);
    // u*=vec2(exp2(floor(u.y*5.)),u.y);
    // float t=texture(tex0,vec2(u.y,0)).r-.3,n=N(u)-t;
    // u.x/=32.;
    // fragColor+=step(0.,n*(t-N(u)));

    // // Convert UV to pixel coordinates
    // vec2 f = v_uv * u_resolution;
    
    // // Normalize coordinates
    // vec2 u = f / u_resolution.y;

    vec2 u = v_uv;
    
    // Apply barcode pattern transformation
    u.y -= mod(u.y, 1.0 / u_noise_scale);
    u *= vec2(exp2(floor(u.y * 5.0)), u.y);
    
    // Sample input fft for modulation
    // float t = texture(tex0, vec2(u.y, 0.0)).r - u_threshold;
    float t = u_fft_bands[int(u.y * 512.0)] - u_threshold;
    float n = N(u) - t;
    
    // Apply barcode width scaling
    u.x /= u_barcode_width;
    
    // Generate final pattern
    float pattern = step(0.0, n * (t - N(u)));
    
    // Apply intensity and output
    fragColor = vec4(vec3(pattern * u_pattern_intensity), 1.0);
}