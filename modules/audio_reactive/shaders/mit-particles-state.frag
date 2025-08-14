#version 330 core
precision highp float;

uniform sampler2D u_state_prev;   // RGBA32F: pos.xy, vel.xy
uniform ivec2     u_tex_size;     // state texture size
uniform int       u_num_particles;

uniform vec2  u_resolution;       // render size (px)
uniform vec2  u_center;           // circle centre in px
uniform float u_radius;           // circle radius (px)
uniform float u_dt;               // seconds
uniform float u_time;             // seconds
uniform float u_audio;            // 0..~2 (excitement)

uniform float u_gravity_strength; // spring strength toward radius (px/s^2)
uniform float u_swirl_strength;   // tangential acceleration (px/s^2)
uniform float u_noise_strength;   // noise acceleration (px/s^2)

out vec4 FragColor;

// Small helpers
uint hashU(uint x){ x ^= x>>16U; x*=0x7feb352dU; x^=x>>15U; x*=0x846ca68bU; x^=x>>16U; return x; }
float hash1(ivec2 p){ return float(hashU(uint(p.x) * 1664525U ^ uint(p.y))) / 4294967296.0; }
vec2  hash2(ivec2 p){ return vec2(hash1(p), hash1(p+17))*2.0-1.0; }

void main() {
    ivec2 uv  = ivec2(gl_FragCoord.xy);                 // 1:1 texel mapping
    int   idx = uv.x + uv.y * u_tex_size.x;
    if (idx >= u_num_particles) { FragColor = vec4(0); return; }

    // First-frame initialization: seed positions on/around the circle with noisy velocities
    bool do_init = (u_time < 0.0005);
    if (do_init) {
        float t = float(idx) / float(max(1, u_num_particles));
        float ang = t * 6.2831853;
        float rj = u_radius + hash1(uv) * 6.0 - 3.0;     // small radial jitter
        vec2 dir = vec2(cos(ang), sin(ang));
        vec2 p0  = u_center + dir * rj;
        vec2 tan = vec2(-dir.y, dir.x);
        // Start with noticeable tangential velocity
        vec2 v0  = tan * (u_swirl_strength * 0.25);
        FragColor = vec4(p0, v0);
        return;
    }

    vec4 s  = texelFetch(u_state_prev, uv, 0);           // pos.xy, vel.xy
    vec2 p  = s.xy;
    vec2 v  = s.zw;

    // --- Forces driving particles toward the circle ---
    vec2  d     = p - u_center;
    float r     = length(d) + 1e-6;
    vec2  dir   = d / r;

    // Spring toward the target radius
    float k     = u_gravity_strength;                    // radial spring strength
    float damp  = 0.92;                                  // velocity damping
    float target= u_radius;
    float radialErr = (target - r);                      // >0 pulls outward, <0 inward
    vec2  F_rad = dir * (k * radialErr);

    // Tangential swirl + audio modulation (mild)
    vec2  tang  = vec2(-dir.y, dir.x);
    float swirl = u_swirl_strength * (1.0 + 0.1 * u_audio);
    vec2  F_tan = tang * swirl;

    // Gentle noise kick (scaled by audio)
    vec2 n  = hash2(uv + ivec2(int(u_time*60.0))) * (u_noise_strength * (0.5 + 0.5 * clamp(u_audio, 0.0, 4.0)));

    // Integrate (semi-implicit Euler)
    vec2 a = F_rad + F_tan + n;
    v = (v + a * u_dt) * damp;

    // Keep speeds bounded
    float vmax = 800.0;
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
