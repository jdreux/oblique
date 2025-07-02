#version 330
/*
Circle Echo Shader
Author: Oblique AI
Description: Renders concentric modulated circles with echo/fade effect. Placeholder uniforms for future audio features.
Inputs:
    u_time: float - Current time
    u_resolution: vec2 - Viewport resolution
    u_n_circles: int - Number of circles
    u_n_points: int - Points per circle (for reference)
    u_mod_depth: float - Modulation depth
    u_echo_decay: float - Echo decay factor
    u_max_echoes: int - Number of echoes
    u_audio_level: float - Placeholder for audio level
    u_band_amps: float[16] - Placeholder for band amplitudes
*/

#ifdef GL_ES
precision mediump float;
#endif

uniform float u_time;
uniform vec2 u_resolution;
uniform int u_n_circles;
uniform float u_mod_depth;
uniform float u_echo_decay;
uniform int u_max_echoes;
uniform float u_audio_level;
uniform float u_band_amps[16];

out vec4 fragColor;

// Utility: draw a soft circle
float circle(vec2 uv, vec2 center, float radius, float thickness) {
    float d = length(uv - center);
    float edge = smoothstep(radius - thickness, radius, d) - smoothstep(radius, radius + thickness, d);
    return edge;
}

// Draws a small square at 'pos' in uv space
float draw_marker(vec2 uv, vec2 pos, float size) {
    vec2 d = abs(uv - pos);
    return step(d.x, size) * step(d.y, size);
}

void main() {
    vec2 uv = (gl_FragCoord.xy / u_resolution.xy) * 2.0 - 1.0;
    uv.x *= u_resolution.x / u_resolution.y;
    // uv.y *= -1.0;
    vec3 color = vec3(0.0);
    float t = u_time;
    vec2 center = vec2(1,1);
    float base_radius = 0.4;
    float echo_alpha = 1.0;
    for (int c = 0; c < 32; ++c) {
        if (c >= u_n_circles) break;
        float radius = base_radius + float(c) * 0.8 / float(u_n_circles);
        float mod = sin(t * 0.7 + float(c) * 0.3 + uv.x * 6.0 + uv.y * 6.0);
        float modulated_radius = radius + u_mod_depth * mod;
        echo_alpha = 1.0;
        for (int e = 0; e < 16; ++e) {
            if (e >= u_max_echoes) break;
            float echo_offset = float(e) * 0.03;
            float echo_radius = modulated_radius - echo_offset;
            float alpha = pow(u_echo_decay, float(e));
            color += circle(uv, center, echo_radius, 0.008) * alpha * vec3(0.0, 0.94, 1.0);
        }
    }
    fragColor = vec4(color, 1.0);
   

    // vec3 marker_color = vec3(1.0, 0.0, 0.0); // red

    // // Draw markers at (0,0), (0.5,0), (0,0.5), (0.5,0.5)
    // color += marker_color * draw_marker(uv, vec2(0.0, 0.0), 0.5);
    // color += vec3(0.0, 1.0, 0.0) * draw_marker(uv, vec2(0.5, 0.0), 0.5);
    // color += vec3(0.0, 0.0, 1.0) * draw_marker(uv, vec2(0.0, 0.5), 0.5);
    // color += vec3(1.0, 1.0, 0.0) * draw_marker(uv, vec2(0.5, 0.5), 0.5);

    //  float c = circle(uv, vec2(0), 0.05, 0.01);
    // fragColor = vec4(vec3(c), 1.0);
} 