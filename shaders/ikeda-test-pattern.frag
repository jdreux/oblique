#version 330

/*
Ikeda Test Pattern Shader (adapted from ShaderToy snippet)
Author: Oblique
Description:
    Renders a high-contrast barcode/test-pattern inspired by Ryoji Ikeda.
    Uses an external noise/data texture (u_noise_texture) to drive horizontal
    glitches. The vertical pattern repeats every 16 rows and introduces thin
    divider lines every 256/0.15 ≈ 42 pixels.

Uniforms:
    u_resolution      vec2   – Render target resolution in pixels.
    u_time            float  – Current time in seconds.
    u_noise_texture   sampler2D – 2-D texture providing random values.
*/

uniform vec2 u_resolution;
uniform float u_time;
uniform sampler2D u_noise_texture;

out vec4 fragColor;

void main() {
    // Original ShaderToy variables renamed:
    //   f          → fragCoord.xy (pixel position)
    //   iResolution → u_resolution
    //   iTime       → u_time
    //   iChannel0   → u_noise_texture

    vec2 f = gl_FragCoord.xy;

    // Normalised coordinates (divide by resolution) and squash vertically by 16.
    vec2 u = (f / u_resolution) / vec2(1.0, 16.0);

    // Texture-driven glitch test pattern.
    float texSample = texture(u_noise_texture, u).r;
    float v = fract(texSample + u_time * 0.5);

    // Horizontal stripes every 256 texels in the compressed vertical axis.
    float stripe = fract(u.y * 256.0);

    // Binary pattern: white if either glitch value < 0.5 OR we’re on a stripe line.
    float pattern = (v < 0.5 || stripe < 0.15) ? 1.0 : 0.0;

    fragColor = vec4(vec3(pattern), 1.0);
} 