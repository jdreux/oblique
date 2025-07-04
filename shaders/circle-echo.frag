#version 330
/*
Circle Shader
Author: Oblique AI
Description: Renders concentric modulated circles. Audio-reactive via band amplitudes.
Inputs:
    u_time: float - Current time
    u_resolution: vec2 - Viewport resolution
    u_n_circles: int - Number of circles
    u_mod_depth: float - Modulation depth
    u_band_amps: float[16] - Band amplitudes
*/

#ifdef GL_ES
precision mediump float;
#endif

uniform float u_time;
uniform vec2 u_resolution;
uniform int u_n_circles;
uniform float u_mod_depth;
uniform float u_band_amps[16];

out vec4 fragColor;

// Utility: draw a soft circle
float circle(vec2 uv, vec2 center, float radius, float thickness) {
    float d = length(uv - center);
    // smoothstep is used here to create a soft, anti-aliased edge for the circle.
    // It smoothly interpolates from 0 to 1 as 'd' moves from (radius - thickness) to (radius),
    // and then back from 1 to 0 as 'd' moves from (radius) to (radius + thickness).
    // The subtraction creates a band of width '2*thickness' centered on 'radius'.
    float edge = smoothstep(radius - thickness, radius, d) - smoothstep(radius, radius + thickness, d);
    return edge;
}

void main() {
    vec2 uv = (gl_FragCoord.xy / u_resolution.xy) * 2.0 - 1.0;
    uv.x *= u_resolution.x / u_resolution.y;
    vec3 color = vec3(0.0);
    float t = u_time;
    vec2 center = vec2(1);
    float base_radius = 0.4;
    for (int c = 0; c < 32; ++c) {
        if (c >= u_n_circles) break;
        int band_idx = c;
        float band_amp = band_idx < 16 ? u_band_amps[band_idx] : 0.0;
        float amp = 0.1 + band_amp * 0.9;
        float radius = base_radius + float(c) * 0.8 / float(u_n_circles);
        float angle = atan(uv.y - center.y, uv.x - center.x);
        // --- Sound wave modulation ---
        // Each circle's radius is modulated by a sine wave to mimic a sound wave.
        // The amplitude of the wave is controlled by the band amplitude.
        // The frequency is mapped to the band index for visual variety.
        float wave_freq = 6.0 + float(band_idx) * 1.5; // Higher bands = more wiggles
        float wave_phase = t * 0.2 + float(band_idx) * 0.3; // Animate the wave
        float wave_amp = .04 + band_amp * 0.2; // Louder = more pronounced wave
        float wave = sin(1 * wave_freq + wave_phase) * .01;
        float modulated_radius = radius + wave_amp + wave;
        float alpha = amp;
        color += circle(uv, center, modulated_radius, 0.008) * alpha * vec3(0.0, 0.94, 1.0);
    }
    fragColor = vec4(color, 1.0);
} 