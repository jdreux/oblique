// Passthrough fragment shader
// Description: Displays a texture to the screen without modification
// Author: Oblique MVP
// Inputs: tex0 (sampler2D), u_time (float), u_resolution (vec2)

#version 330 core

uniform sampler2D tex0;
uniform float u_time;
uniform vec2 u_resolution;

// in vec2 fragCoord;
out vec4 fragColor;

void main() {
    // vec2 uv = fragCoord / u_resolution;
    vec2 uv = gl_FragCoord.xy / u_resolution.xy;
    fragColor = texture(tex0, uv);
} 