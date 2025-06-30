/*
Pauric Particles Shader
Author: Oblique AI
Description: Sprinkle of particles emanating from one corner and spreading across the screen.
Inputs:
    uniform float u_time;           // Current time in seconds
    uniform vec2  u_resolution;     // Viewport resolution (width, height)
    uniform int   u_num_particles;  // Number of particles
    uniform float u_spread;         // Spread factor (0.0 to 1.0)
    uniform float u_speed;          // Speed multiplier
*/

#version 330 core
precision highp float;

uniform float u_time;
uniform vec2  u_resolution;
uniform int   u_num_particles;
uniform float u_spread;
uniform float u_speed;

out vec4 fragColor;

// Hash function for pseudo-randomness
float hash(float n) {
    return fract(sin(n) * 43758.5453123);
}

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution.xy;
    float aspect = u_resolution.x / u_resolution.y;
    uv.x *= aspect;

    float min_dist = 1.0;
    for (int i = 0; i < 512; ++i) {
        if (i >= u_num_particles) break;
        float fi = float(i);
        float t = u_time * u_speed + fi * 10.0;
        float angle = hash(fi) * 3.14159 * 2.0 * u_spread;
        float radius = hash(fi + 1.0) * 0.4 + 0.1;
        float life = mod(u_time * u_speed + hash(fi + 2.0) * 100.0, 1.0);
        float px = radius * life * cos(angle);
        float py = radius * life * sin(angle);
        // Emanate from bottom-left corner
        vec2 center = vec2(0.05, 0.05);
        vec2 pos = center + vec2(px, py);
        pos.x *= aspect;
        float d = length(uv - pos);
        min_dist = min(min_dist, d);
    }
    float particle = smoothstep(0.02, 0.0, min_dist);
    fragColor = vec4(vec3(particle), 1.0);
} 