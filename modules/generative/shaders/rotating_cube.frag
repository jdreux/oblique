#version 330 core

in vec2 v_uv;
out vec4 frag_color;

uniform vec2 u_resolution;
uniform float u_time;
uniform float u_speed;
uniform float u_edge_width;
uniform float u_cube_size;
uniform float u_amplitude;
uniform float u_bass;
uniform float u_centroid;
uniform float u_explode;

// 3D rotations
mat3 rot_y(float a) {
    float c = cos(a), s = sin(a);
    return mat3(c, 0.0, s, 0.0, 1.0, 0.0, -s, 0.0, c);
}
mat3 rot_x(float a) {
    float c = cos(a), s = sin(a);
    return mat3(1.0, 0.0, 0.0, 0.0, c, -s, 0.0, s, c);
}
mat3 rot_z(float a) {
    float c = cos(a), s = sin(a);
    return mat3(c, -s, 0.0, s, c, 0.0, 0.0, 0.0, 1.0);
}

// 4D rotations — these create the hyperdimensional projection effect
// XW plane rotation
void rot_xw(inout vec4 p, float a) {
    float c = cos(a), s = sin(a);
    float x = p.x;
    p.x = c * x - s * p.w;
    p.w = s * x + c * p.w;
}
// YW plane rotation
void rot_yw(inout vec4 p, float a) {
    float c = cos(a), s = sin(a);
    float y = p.y;
    p.y = c * y - s * p.w;
    p.w = s * y + c * p.w;
}
// ZW plane rotation
void rot_zw(inout vec4 p, float a) {
    float c = cos(a), s = sin(a);
    float z = p.z;
    p.z = c * z - s * p.w;
    p.w = s * z + c * p.w;
}
// XY plane rotation (4D)
void rot_xy(inout vec4 p, float a) {
    float c = cos(a), s = sin(a);
    float x = p.x;
    p.x = c * x - s * p.y;
    p.y = s * x + c * p.y;
}
// XZ plane rotation (4D)
void rot_xz(inout vec4 p, float a) {
    float c = cos(a), s = sin(a);
    float x = p.x;
    p.x = c * x - s * p.z;
    p.z = s * x + c * p.z;
}
// YZ plane rotation (4D)
void rot_yz(inout vec4 p, float a) {
    float c = cos(a), s = sin(a);
    float y = p.y;
    p.y = c * y - s * p.z;
    p.z = s * y + c * p.z;
}

// Perspective project 4D → 3D (stereographic-ish)
vec3 project_4to3(vec4 p) {
    float d4 = 2.5;
    float scale = d4 / (d4 - p.w);
    return p.xyz * scale;
}

// Perspective project 3D → 2D
vec2 project_3to2(vec3 p) {
    float d3 = 4.0;
    float scale = d3 / (d3 + p.z);
    return p.xy * scale;
}

float seg_dist(vec2 p, vec2 a, vec2 b) {
    vec2 ab = b - a;
    vec2 ap = p - a;
    float t = clamp(dot(ap, ab) / dot(ab, ab), 0.0, 1.0);
    return length(ap - ab * t);
}

void main() {
    vec2 uv = (gl_FragCoord.xy - 0.5 * u_resolution) / min(u_resolution.x, u_resolution.y);

    float t = u_time * u_speed;
    float s = u_cube_size + u_bass * 0.06;

    // ---- 16 tesseract vertices: all combinations of ±s in 4D ----
    vec4 v[16];
    for (int i = 0; i < 16; i++) {
        v[i] = vec4(
            ((i & 1) == 0) ? -s : s,
            ((i & 2) == 0) ? -s : s,
            ((i & 4) == 0) ? -s : s,
            ((i & 8) == 0) ? -s : s
        );
    }

    // ---- 4D rotations ----
    // Audio modulates velocity (multiplier), not position — no snapping.
    // Bass opens up the W-axis fold; centroid and amplitude add drift.
    float bass_vel = 1.0 + u_bass * 2.0;
    float cent_vel = 1.0 + u_centroid * 1.5;
    float amp_vel = 1.0 + u_amplitude * 1.0;

    // Base tumble through 3D planes
    float a_xz = t * 0.5;
    float a_yz = t * 0.3;
    float a_xy = t * 0.2;
    // W-axis planes: speed scales with audio, creating smooth acceleration
    float a_xw = t * 0.4 * bass_vel;
    float a_yw = t * 0.25 * cent_vel;
    float a_zw = t * 0.15 * amp_vel;

    for (int i = 0; i < 16; i++) {
        rot_xz(v[i], a_xz);
        rot_yz(v[i], a_yz);
        rot_xy(v[i], a_xy);
        rot_xw(v[i], a_xw);
        rot_yw(v[i], a_yw);
        rot_zw(v[i], a_zw);
    }

    // ---- Explode: push vertices outward on transients ----
    float explode_amt = u_explode * u_amplitude * 0.12;
    for (int i = 0; i < 16; i++) {
        vec4 dir = normalize(v[i]);
        v[i] += dir * explode_amt;
    }

    // ---- Project 4D → 3D → 2D ----
    vec2 p[16];
    float w_depth[16];  // store W-depth for brightness variation
    for (int i = 0; i < 16; i++) {
        w_depth[i] = v[i].w;
        vec3 p3 = project_4to3(v[i]);
        p[i] = project_3to2(p3);
    }

    // ---- 32 edges of the tesseract ----
    // Two vertices share an edge iff they differ in exactly 1 coordinate.
    // Encode as pairs: 12 edges of inner cube (w=-s), 12 of outer (w=+s), 8 connecting.
    int edges[64] = int[64](
        // Inner cell (w = -s): vertices 0-7
        0,1, 0,2, 1,3, 2,3,
        4,5, 4,6, 5,7, 6,7,
        0,4, 1,5, 2,6, 3,7,
        // Outer cell (w = +s): vertices 8-15
        8,9,  8,10,  9,11, 10,11,
        12,13, 12,14, 13,15, 14,15,
        8,12, 9,13, 10,14, 11,15,
        // Connecting edges (differ only in w)
        0,8, 1,9, 2,10, 3,11,
        4,12, 5,13, 6,14, 7,15
    );

    float pw = (u_edge_width + u_amplitude * 2.5) / min(u_resolution.x, u_resolution.y);

    // Accumulate edge brightness with depth-dependent intensity
    float brightness = 0.0;
    float glow_acc = 0.0;

    for (int i = 0; i < 32; i++) {
        int a = edges[i * 2];
        int b = edges[i * 2 + 1];
        float d = seg_dist(uv, p[a], p[b]);

        // Depth fade: edges closer in W feel brighter
        float avg_w = (w_depth[a] + w_depth[b]) * 0.5;
        float depth_fade = smoothstep(-s * 2.0, s * 2.0, avg_w) * 0.5 + 0.5;

        float edge = (1.0 - smoothstep(0.0, pw, d)) * depth_fade;
        brightness += edge;

        // Glow per edge
        float glow = exp(-d * 60.0 * (1.0 - u_amplitude * 0.4)) * depth_fade;
        glow_acc += glow;
    }

    brightness = clamp(brightness, 0.0, 1.0);
    glow_acc = clamp(glow_acc * u_amplitude * 0.15, 0.0, 1.0);

    // Color: cool blue → warm white driven by spectral centroid
    vec3 cool = vec3(0.35, 0.55, 1.0);
    vec3 warm = vec3(1.0, 0.85, 0.6);
    vec3 tint = mix(cool, warm, u_centroid);

    vec3 color = brightness * vec3(1.0) + glow_acc * tint;

    frag_color = vec4(color, 1.0);
}
