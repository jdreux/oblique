#version 330 core
precision highp float;

uniform sampler2D u_state;       // RGBA32F: pos.xy, vel.xy
uniform ivec2     u_texSize;     // state texture size
uniform int       u_numParticles;

uniform vec2  u_resolution;      // framebuffer size (px)
uniform float u_pointSizePx;     // base point size
uniform float u_sizeSpeedScale;  // size multiplier based on velocity
uniform float u_softness;        // falloff exponent
uniform vec3  u_tint;            // particle colour
uniform float u_exposure;        // tone mapping strength

out vec4 FragColor;

float softDisc(vec2 d, float rPx, float softness) {
    float r2 = dot(d, d);
    float s2 = rPx * rPx * 0.25;
    float g  = exp(-r2 / max(1e-6, (2.0*s2)));
    return pow(g, clamp(softness, 1.0, 8.0));
}

void main() {
    vec2 fragPx = gl_FragCoord.xy;
    float accum = 0.0;

    for (int i = 0; i < u_numParticles; ++i) {
        ivec2 uv = ivec2(i % u_texSize.x, i / u_texSize.x);
        vec4 s   = texelFetch(u_state, uv, 0);  // pos.xy, vel.xy
        vec2 p   = s.xy;
        vec2 v   = s.zw;

        float speed = length(v);
        float rPx   = u_pointSizePx * (1.0 + u_sizeSpeedScale * clamp(speed/400.0, 0.0, 2.0));

        vec2 d = p - fragPx;
        if (abs(d.x) > rPx || abs(d.y) > rPx) continue;

        accum += softDisc(d, rPx, u_softness);
    }

    float l = 1.0 - exp(-u_exposure * accum);
    FragColor = vec4(u_tint * l, l); // premultiplied-style, works well with additive blending
}
