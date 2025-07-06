#version 330
/*
Spectral Visualizer Shader
Author: Oblique AI
Inputs:
    uniform float u_time;           // Current time in seconds
    uniform vec2 u_resolution;      // Output resolution (width, height)
    uniform float u_bands[512];     // FFT band amplitudes (normalized 0..1)
    uniform int u_num_bands;        // Number of bands (should be 512)
Description:
    Renders a frequency spectrum with colored bars, mapping frequency to color and amplitude to height.
*/

uniform float u_time;
uniform vec2 u_resolution;
uniform float u_bands[512];
uniform int u_num_bands;
out vec4 fragColor;
in vec2 v_uv;

vec3 bandColor(float normIdx) {
    // normIdx: 0.0 (low freq, left) to 1.0 (high freq, right)
    // Blue → Green → Yellow → Red
    // if (normIdx < 0.33) {
    //     return mix(vec3(0.0, 1.0, 1.0), vec3(0.0, 1.0, 0.0), normIdx / 0.33); // Cyan to Green
    // } else if (normIdx < 0.66) {
    //     return mix(vec3(0.0, 1.0, 0.0), vec3(1.0, 1.0, 0.0), (normIdx - 0.33) / 0.33); // Green to Yellow
    // } else {
    //     return mix(vec3(1.0, 1.0, 0.0), vec3(1.0, 0.0, 0.5), (normIdx - 0.66) / 0.34); // Yellow to Pinkish Red
    // }
    return vec3(1);
}

void main() {
    // vec2 uv = gl_FragCoord.xy / u_resolution;
    vec2 uv = v_uv;
    float bandW = 1.0 / float(u_num_bands);
    int bandIdx = int(floor(uv.x * float(u_num_bands)));
    // clamp() ensures bandIdx stays within valid array bounds [0, u_num_bands-1]
    // This prevents accessing invalid memory locations in the u_bands array
    bandIdx = clamp(bandIdx, 0, u_num_bands - 1);
    float bandLevel = u_bands[bandIdx];
    float barHeight = bandLevel * 0.95; // 95% of vertical space
    float yNorm = 1.0 - uv.y;
    float normIdx = float(bandIdx) / float(u_num_bands - 1);
    vec3 color = bandColor(normIdx);
    float alpha = smoothstep(barHeight, barHeight + 0.01, yNorm);
    // Grid lines (horizontal)
    float grid = step(0.01, abs(fract(uv.y * 10.0) - 0.5) - 0.49);
    color = mix(color, vec3(0.1), grid * 0.2);
    // Fade out background
    color = mix(vec3(0.05), color, alpha);
    fragColor = vec4(color, 1.0);
} 