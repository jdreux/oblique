#version 330 core
precision highp float;

uniform sampler2D u_statePrev;   // RGBA32F: pos.xy, vel.xy
uniform ivec2     u_texSize;     // state texture size
uniform int       u_numParticles;

uniform vec2  u_resolution;      // render size (px)
uniform vec2  u_center;          // circle centre in px
uniform float u_radius;          // circle radius (px)
uniform float u_dt;              // seconds
uniform float u_time;            // seconds
uniform float u_audio;           // 0..~2 (excitement)

out vec4 FragColor;

// Small helpers
uint hashU(uint x){ x ^= x>>16U; x*=0x7feb352dU; x^=x>>15U; x*=0x846ca68bU; x^=x>>16U; return x; }
float hash1(ivec2 p){ return float(hashU(uint(p.x) * 1664525U ^ uint(p.y))) / 4294967296.0; }
vec2  hash2(ivec2 p){ return vec2(hash1(p), hash1(p+17))*2.0-1.0; }

void main() {
    ivec2 uv  = ivec2(gl_FragCoord.xy);                 // 1:1 texel mapping
    int   idx = uv.x + uv.y * u_texSize.x;
    if (idx >= u_numParticles) { FragColor = vec4(0); return; }

    vec4 s  = texelFetch(u_statePrev, uv, 0);           // pos.xy, vel.xy
    vec2 p  = s.xy;
    vec2 v  = s.zw;

    // --- Forces driving particles toward the circle ---
    vec2  d     = p - u_center;
    float r     = length(d) + 1e-6;
    vec2  dir   = d / r;

    // Spring toward the target radius
    float k     = 6.0;                                  // radial spring strength
    float damp  = 0.86;                                 // velocity damping
    float target= u_radius;
    float radialErr = (target - r);                     // >0 pulls outward, <0 inward
    vec2  F_rad = dir * (k * radialErr);

    // Tangential “swirl” + audio excitation noise
    vec2  tang  = vec2(-dir.y, dir.x);
    float swirl = 1.4 + 2.0 * u_audio;                  // more swirl with audio
    vec2  F_tan = tang * swirl;

    // Gentle noise kick (scaled by audio)
    vec2 n  = hash2(uv + ivec2(int(u_time*60.0))) * (2.0 + 8.0*u_audio);

    // Integrate (semi-implicit Euler)
    vec2 a = F_rad + F_tan + n;
    v = (v + a * u_dt) * damp;

    // Keep speeds bounded
    float vmax = 600.0;
    float spd  = length(v);
    if (spd > vmax) v *= vmax / spd;

    p += v * u_dt;

    // Soft wrap to keep cloud compact
    vec2 wrapMin = u_center - vec2(u_radius*2.0);
    vec2 wrapMax = u_center + vec2(u_radius*2.0);
    if (p.x < wrapMin.x) p.x = wrapMax.x;
    if (p.x > wrapMax.x) p.x = wrapMin.x;
    if (p.y < wrapMin.y) p.y = wrapMax.y;
    if (p.y > wrapMax.y) p.y = wrapMin.y;

    FragColor = vec4(p, v);
}
