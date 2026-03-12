#version 330 core

in vec2 v_uv;
out vec4 frag_color;

uniform vec2 u_resolution;
uniform float u_time;
uniform float u_speed;
uniform float u_n_folds;
uniform float u_scale;
uniform float u_fold_depth;
uniform float u_amplitude;
uniform float u_bass;
uniform float u_centroid;

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

// Rotation matrix — computed once in main, used by map()
mat3 g_rot;

float map(vec3 p) {
    p = g_rot * p;

    float r = length(p);
    // Guard against pole singularities
    float safe_r = max(r, 0.0001);
    float theta = acos(clamp(p.y / safe_r, -1.0, 1.0));
    float phi = atan(p.z, p.x);

    // Strong pole guard: zero out all lobe modulation near poles
    float pole_guard = smoothstep(0.0, 0.4, theta) * smoothstep(3.14159, 2.74, theta);

    float n = u_n_folds;
    float depth = u_fold_depth + u_bass * 0.08;

    // Calabi-Yau cross-section: spherical harmonics-inspired multi-lobe surface.
    // Primary n-fold lobe structure
    float lobe1 = cos(n * phi) * sin(theta * 2.0);
    // Secondary cross-lobe: creates the deep folds between petals
    float lobe2 = cos(n * phi * 2.0) * sin(theta) * 0.5;
    // Tertiary: diagonal interlocking for the "crumpled" quality
    float lobe3 = cos(n * phi + n * theta * 0.7) * pole_guard;

    float breathe = u_amplitude * 0.04;
    float target_r = u_scale + breathe
        + depth * lobe1 * pole_guard
        + depth * 0.5 * lobe2 * pole_guard
        + depth * 0.35 * lobe3;

    return r - target_r;
}

vec3 calc_normal(vec3 p) {
    vec2 e = vec2(0.002, 0.0);
    return normalize(vec3(
        map(p + e.xyy) - map(p - e.xyy),
        map(p + e.yxy) - map(p - e.yxy),
        map(p + e.yyx) - map(p - e.yyx)
    ));
}

float raymarch(vec3 ro, vec3 rd) {
    float t = 0.0;
    for (int i = 0; i < 96; i++) {
        float d = map(ro + rd * t);
        if (abs(d) < 0.0008) return t;
        t += abs(d) * 0.5;
        if (t > 6.0) break;
    }
    return -1.0;
}

void main() {
    vec2 uv = (gl_FragCoord.xy - 0.5 * u_resolution) / min(u_resolution.x, u_resolution.y);

    float t = u_time * u_speed;
    float bass_vel = 1.0 + u_bass * 1.5;
    float cent_vel = 1.0 + u_centroid * 1.0;

    g_rot = rot_y(t * 0.5 * bass_vel)
          * rot_x(t * 0.35 * cent_vel)
          * rot_z(t * 0.2);

    // Camera
    vec3 ro = vec3(0.0, 0.0, 1.8);
    vec3 rd = normalize(vec3(uv, -1.2));

    float hit = raymarch(ro, rd);

    vec3 color = vec3(0.0);

    // Color palette: warm pink → cool cyan
    vec3 warm = vec3(1.0, 0.5, 0.7);
    vec3 cool = vec3(0.5, 0.9, 1.0);
    vec3 tint = mix(warm, cool, u_centroid);

    // Track closest approach for glow (works for both hit and miss)
    float closest = 1e9;
    {
        float tt = 0.0;
        for (int i = 0; i < 80; i++) {
            float d = map(ro + rd * tt);
            closest = min(closest, abs(d));
            tt += max(abs(d) * 0.6, 0.002);
            if (tt > 6.0) break;
        }
    }

    if (hit > 0.0) {
        vec3 p = ro + rd * hit;
        vec3 n = calc_normal(p);

        // Fresnel: silhouette edges only
        float fresnel = 1.0 - abs(dot(n, -rd));
        float edge = smoothstep(0.5, 0.95, fresnel);

        // Parametric grid lines on the surface
        vec3 sp = g_rot * p;
        float r_sp = length(sp);
        float theta = acos(clamp(sp.y / max(r_sp, 0.001), -1.0, 1.0));
        float phi = atan(sp.z, sp.x);

        float n_folds = u_n_folds;
        float lw = 0.015;  // line width in parameter space
        // Latitude lines
        float line_theta = 1.0 - smoothstep(0.0, lw, abs(fract(theta * 5.0 + 0.5) - 0.5));
        // Longitude lines (n-fold symmetric)
        float line_phi = 1.0 - smoothstep(0.0, lw, abs(fract(phi * n_folds / 6.2832 * 2.5 + 0.5) - 0.5));
        float grid = clamp(line_theta + line_phi, 0.0, 1.0);

        // Wireframe only — no fill at all
        float wire = clamp(edge + grid, 0.0, 1.0);
        wire *= 0.6 + u_amplitude * 0.6;

        color = wire * tint;
    }

    // Glow halo — only when audio is present, tight falloff
    float halo = exp(-closest * 50.0) * u_amplitude * 0.35;
    color += halo * tint;

    frag_color = vec4(color, 1.0);
}
