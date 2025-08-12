#version 330

/*
Protoplasm Shader (ported from ShaderToy)
Author: Adapted by Oblique AI Agent (original unknown)
Description:
    Organic, audio-reactive volumetric pattern rendered via ray marching and
    procedural FBM noise.  Based on a ShaderToy snippet, adapted to Oblique's
    uniform interface and GLSL 3.30 requirements.

Inputs (uniforms)
    uniform vec2  u_resolution   – Render target resolution in pixels.
    uniform float u_time         – Current time in seconds.
    uniform sampler2D u_texture       – Channel-0 texture source.

Outputs
    out vec4 fragColor           – Final RGBA fragment colour.
*/

// -----------------------------------------------------------------------------
// Uniforms & I/O
// -----------------------------------------------------------------------------
uniform vec2  u_resolution;
uniform float u_time;
uniform sampler2D u_noise_texture;

out vec4 fragColor;

// Reduce FBM octaves for better performance but lower detail
#define FBM_OCTAVES 4

// LYGIA simplex noise implementation
#include "lygia/generative/snoise.glsl"
// LYGIA fractal brownian motion implementation
#include "lygia/generative/fbm.glsl"

// -----------------------------------------------------------------------------
// Utility macros & constants (ported from ShaderToy snippet)
// -----------------------------------------------------------------------------
#define T u_time                                           // rename iTime → u_time
#define r(v,t) { float _a=(t)*T; float _c=cos(_a); float _s=sin(_a); v*=mat2(_c,_s,-_s,_c); }
#define SQRT3_2 1.26                                       // ≈ √3 / 2
#define SQRT2_3 1.732                                      // ≈ √2 * √3 (unused but kept)
#define smin(a,b) (1.0/(1.0/(a)+1.0/(b)))                  // smooth-minimum helper

// -----------------------------------------------------------------------------
// FBM / Noise (Inigo Quilez – CC BY-NC-SA 3.0)
// -----------------------------------------------------------------------------
const mat3 m = mat3( 0.00,  0.80,  0.60,
                    -0.80,  0.36, -0.48,
                    -0.60, -0.48,  0.64 );


// float sfbm(vec3 p) {
//     float f = 0.0;
//     f  = 0.5000 * snoise(p);  p = m * p * 2.02;
//     f += 0.2500 * snoise(p);  p = m * p * 2.03;
//     f += 0.1250 * snoise(p);  p = m * p * 2.01;
//     f += 0.0625 * snoise(p);
//     return f;
// }

// #define sfbm3(p) vec3(sfbm(p), sfbm((p) - 327.67), sfbm((p) + 327.67))

// -----------------------------------------------------------------------------
// Ray-marcher core (adapted from Trisomie21 https://www.shadertoy.com/view/4tfGRB)
// -----------------------------------------------------------------------------

const vec4 BG_COLOUR = vec4(0.0, 0.0, 0.0, 0.0);           // background tint

void mainImage(out vec4 f, vec2 fragCoord) {
    // ---------------------------------------------------------------------
    // Initial ray setup
    // ---------------------------------------------------------------------
    // Replicate original ShaderToy maths: convert pixel-coords → [-0.5, +0.5]
    vec4 p = vec4(fragCoord, 0.0, 1.0) /                      // (x,y,0,1)
             vec4(u_resolution.y, u_resolution.y,             // aspect-flatten X & Y by height
                  u_resolution.x, u_resolution.y) - 0.5;

    vec4 d = p;                          // ray direction (will stay normalised)
    p.z  += 10.0;                        // camera origin (push forward)

    f = BG_COLOUR;                       // initialise output colour

    float x1, x2, x = 1e9;

    // Sample texture for colour modulation (repeat assumed)
    // move back out loop with t.xy -> p.xy to add the visual artefacts
    vec4 c = 5.0 * texture(u_noise_texture, p.xy).rrrr;


    float time_factor = 0.6 + 8.0 * (0.5 - 0.5 * cos(T / 16.0));
    // ray-marching loop. change the decrement to trade-off performance vs. detail.
    for (float i = 1.0; i > 0.0; i -= 0.03) {
        // Early-exit once colour is nearly opaque (performance)
        if (f.x >= 0.9) {
            break;
        }

        // Voxel / cell indexing & local copy of position (t)
        vec4 u = 0.03 * floor(p / vec4(8.0, 8.0, 1.0, 1.0) + 3.5);
        vec4 t = p;

        // Apply object rotations via macro r()
        r(t.xy, u.x);
        r(t.xz, u.y);
        // Additional rotation on (t.yz) could be added if desired

        if(int(i * 100) % 5 == 0) {
            // Sample texture for colour modulation, in local cache for performance.
            // move back out loop with t.xy -> p.xy to add the visual artefacts
            c = 5.0 * texture(u_noise_texture, t.xy).rrrr;
        }

        // Perturb space with signed FBM field
        t.xyz += fbm(t.xyz / 2.0 + vec3(0.5 * T, 0.0, 0.0)) *
                time_factor;

        
        float l2 = dot(t.xyz, t.xyz) - 49.0;
        
        // Optimisation: skip if outside bounding sphere
        if ((l2 > 0.1) && (p.z < 0.0)) {
            break;
        }

        // Distance estimation
        x1 = length(t.xyz) - 7.0;
        x  = abs(mod(length(t.xyz), 1.0) - 0.5);        
        x  = max(x, x1);

        // Hit test
        if (x < 0.01) {
            f += (1.0 - f) * 0.2 * mix(BG_COLOUR, c, i * i);
            x = 0.1;                     // push forward to avoid self-intersection
        }

        // March ray forward
        p += d * x;
    }
}

// -----------------------------------------------------------------------------
// Main entry point
// -----------------------------------------------------------------------------
void main() {
    // Center uv coordinates: (0,0) at screen center, range [-1,1]
    vec2 uv = (gl_FragCoord.xy);
    vec4 colour;
    mainImage(colour, uv);
    fragColor = colour;
}

