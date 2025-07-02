/*
additive-blend.frag
Description: Additively blends two input textures.
Author: Oblique AI Agent
Inputs:
    uniform sampler2D tex0; // First input texture
    uniform sampler2D tex1; // Second input texture
    uniform vec2 u_resolution; // Output resolution
*/
#version 330 core
uniform sampler2D tex0;
uniform sampler2D tex1;
in vec2 v_uv;
out vec4 fragColor;
void main() {
    vec4 color0 = texture(tex0, v_uv);
    vec4 color1 = texture(tex1, v_uv);
    fragColor = min(color0 + color1, 1.0);
}