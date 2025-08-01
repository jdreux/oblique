#version 330
/*
ryoji-lines.frag
Description: Renders animated parallel lines representing FFT frequency bands.
Each line corresponds to a frequency band and animates vertically based on amplitude.
Lines are arranged horizontally with configurable spacing and thickness.
Author: Oblique AI Agent
Inputs:
    - uniform float u_time; // Animation time in seconds
    - uniform vec2 u_resolution; // Viewport resolution
    - uniform float u_bands[512]; // FFT band amplitudes (0.0 to 1.0)
    - uniform int u_num_bands; // Number of bands
    - uniform float u_line_thickness; // Thickness of each line
    - uniform float u_line_spacing; // Spacing between lines
    - uniform float u_animation_speed; // Speed of vertical animation
    - uniform float u_fade_rate; // Rate of fade/trail effect
*/

out vec4 fragColor;

#ifdef GL_ES
precision mediump float;
#endif

uniform float u_time;
uniform vec2 u_resolution;
uniform float u_bands[512];
uniform int u_num_bands;
uniform float u_line_thickness = 0.01;
uniform float u_animation_speed = 0.05;
uniform float u_fade_rate = 0.3;
uniform float u_spectral_brightness = 0.5;

// Function to get band amplitude with bounds checking
float getBandAmplitude(int bandIndex) {
    if (bandIndex >= 0 && bandIndex < u_num_bands) {
        return u_bands[bandIndex];
    }
    return 0.0;
}

// Function to calculate line position and intensity
vec2 calculateLine(vec2 uv, int bandIndex) {
    // Early exit for zero amplitude bands
    float amplitude = getBandAmplitude(bandIndex);
    if (amplitude < 0.01) return vec2(0.0, 0.0);
    
    // Calculate horizontal position for this band - equally allocate each band across viewport width
    float bandWidth = 1.0 / float(u_num_bands)*2;
    float normalizedX = (float(bandIndex) + 0.5) * bandWidth;
    
    // Calculate vertical animation based on amplitude and time
    float animOffset = u_time * u_animation_speed * u_spectral_brightness * (0.5 + amplitude * 0.5);
    // fract() returns the fractional part of a number (part after decimal point)
    // This creates a repeating pattern that wraps around the screen
    float lineY = fract(uv.y + animOffset);
    
    // Create a moving wave pattern based on amplitude
    float wave = sin(lineY * 6.28318 + u_time * 2.0) * 0.5 + 0.5;
    float intensity = amplitude * wave;
    
    // Calculate distance from the line center (horizontal lines)
    float lineCenterX = normalizedX;
    float distFromLine = abs(uv.x - lineCenterX);
    
    // Create the line with thickness and fade
    // smoothstep(edge0, edge1, x) performs smooth Hermite interpolation between 0 and 1
    // when edge0 < x < edge1. Returns 0 when x <= edge0, 1 when x >= edge1
    // Here: creates a smooth falloff from center (0.0) to edge (u_line_thickness)
    float lineMask = smoothstep(u_line_thickness, 0.0, distFromLine);
    
    // Add trail effect based on fade rate
    float trail = smoothstep(1.0, u_fade_rate, lineY);
    
    return vec2(lineMask * intensity * trail, intensity);
}

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution.xy;
    
    // Initialize color (black background)
    vec3 color = vec3(0.0);
    
    // Render each spectral line
    for (int i = 0; i < u_num_bands; i++) {
        vec2 lineResult = calculateLine(uv, i);
        float lineMask = lineResult.x;
        // float intensity = lineResult.y;
        float intensity = getBandAmplitude(i);
        
        // White lines
        vec3 lineColor = vec3(1.0);
        
        // Add this line to the final color
        color += lineColor * lineMask * intensity;
    }
    
    // Clamp and output
    color = clamp(color, 0.0, 1.0);
    fragColor = vec4(color, 1.0);
} 