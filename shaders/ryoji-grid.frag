#version 330
/*
ryoji-grid.frag
Description: Minimal animated grid inspired by Ryoji Ikeda. Black and white, high contrast.
Author: Oblique AI Agent
Inputs:
    - uniform float u_time; // Animation time in seconds
    - uniform vec2 u_resolution; // Viewport resolution
*/

out vec4 fragColor;

#ifdef GL_ES
precision mediump float;
#endif

uniform float u_time;
uniform vec2 u_resolution;

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution.xy;
    float grid_x = step(0.05, abs(sin(uv.x * 40.0 + u_time * 2.0)));
    float grid_y = step(0.05, abs(sin(uv.y * 40.0 + u_time * 2.0)));
    float grid = grid_x * grid_y;
    float color = 1.0 - grid;
    fragColor = vec4(vec3(color), 1.0);
} 