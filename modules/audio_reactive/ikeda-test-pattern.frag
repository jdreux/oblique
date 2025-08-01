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

#define NUM_BARS 32
#define VERTICAL_HEIGHT 256.0

out vec4 fragColor;

void main() {
//     vec2 f = gl_FragCoord.xy;
//     vec2 u=(f/u_resolution.xy) / vec2(1.0, 8.0);
//     fragColor=vec4((fract(texture(u_noise_texture,u).r+u_time*.5)<.5||fract(u.y*256.)<.15)?1.0:0.0);
// }

    // Original ShaderToy variables renamed:
    //   f          → fragCoord.xy (pixel position)
    //   iResolution → u_resolution
    //   iTime       → u_time
    //   iChannel0   → u_noise_texture

    vec2 f = gl_FragCoord.xy;

    // Normalised coordinates (divide by resolution) and squash vertically. 
    vec2 u = (f / u_resolution) / vec2(1.0, VERTICAL_HEIGHT/NUM_BARS);

    // Texture-driven glitch test pattern.
    // Per-bar texture sampling on y axis.  
    float texSample = texture(u_noise_texture, vec2(u.x, floor(u.y*VERTICAL_HEIGHT) / float(NUM_BARS))).r;
    // float v = fract(texSample + u_time * 0.5);
    float v = fract(texSample);

    // Horizontal stripes every VERTICAL_HEIGHT texels in the compressed vertical axis.
    float stripe = fract(u.y * VERTICAL_HEIGHT);

    // Binary pattern: white if either glitch value < 0.5 OR we’re on a stripe line.
    float pattern = (v < 0.5 || stripe < 0.15) ? 1.0 : 0.0;

    fragColor = vec4(vec3(pattern), 1.0);
} 