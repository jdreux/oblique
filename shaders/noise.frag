#version 330

/*
Noise Shader
Author: Oblique
Description: Procedural animated grayscale noise.  Uses LYGIA simplex noise (snoise)
             to generate smooth noise that evolves slowly over time.  Intended to
             be rendered to an off-screen texture and sampled by other modules.

Inputs (Uniforms)
  u_resolution   vec2   – Render target resolution in pixels.
  u_time         float  – Current time in seconds.
*/

// ---- Uniforms --------------------------------------------------------------
uniform vec2  u_resolution;
uniform float u_time;

// ---- Includes --------------------------------------------------------------
// LYGIA simplex noise implementation
#include "lygia/generative/snoise.glsl"

// ---- Outputs ---------------------------------------------------------------
out vec4 fragColor;

// Scale UV to control noise frequency; tweak for desired granularity
const float NOISE_SCALE = 4096;        // higher = finer noise
const float TIME_SPEED  = 0.85;        // speed of temporal evolution

// ---- Main ------------------------------------------------------------------
void main() {
    // Normalized coordinates in [0,1]
    vec2 uv = gl_FragCoord.xy / u_resolution;

    // 3-D simplex noise: use (uv * scale, time) as input
    float n = snoise(vec3(uv * NOISE_SCALE, u_time * TIME_SPEED));

    // Map from [-1,1] → [0,1]
    n = 0.5 + 0.5 * n;

    // Output grayscale noise
    fragColor = vec4(vec3(n), 1.0);
}
