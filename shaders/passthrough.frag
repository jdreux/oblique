// Passthrough fragment shader
// Description: Displays a texture to the screen without modification
// Author: Oblique MVP
// Inputs: tex0 (sampler2D), u_time (float), u_resolution (vec2)

#version 330 core

uniform sampler2D u_texture;
uniform float u_time;
uniform vec2 u_resolution;

in vec2 v_uv;
out vec4 fragColor;

void main() {
    fragColor = texture(u_texture, v_uv);
} 