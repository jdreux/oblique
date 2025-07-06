#version 330 core
/*
Circle Shader  — Oblique AI (2025-07)
Re-implements the visual logic of visual_render_vispy.py in GLSL.
Uniforms
--------
  u_time        Seconds since start.
  u_resolution  Viewport in pixels.
  u_n_circles   How many concentric rings to draw (≤16).
  u_band_amps   16-element array, each ∈ [0,1] (already log-scaled).
*/

#ifdef GL_ES
precision mediump float;
#endif

uniform float      u_time;
uniform vec2       u_resolution;
uniform int        u_n_circles;
uniform float      u_band_amps[16];

out vec4 fragColor;
in  vec2 v_uv;

/* ========== tweakables matching the Python defaults ==================== */
const float MOD_DEPTH = 0.08;              // same as Python
const float LINE_WIDTH = 0.0025;           // visual line thickness
const vec3  C_START = vec3(1.0);            // white
const vec3  C_END   = vec3(0.0, 0.94, 1.0); // cyan

/* Return white-→-cyan gradient, identical to Python code */
vec3 bandColour (int i, int n) {
    float t = n > 1 ? float(i) / float(n - 1) : 0.0;
    return mix(C_START, C_END, t);
}

/* ----------------------------------------------------------------------- */
void main()
{
    /* 1. Normalised coordinate system (square), centred at origin --------*/
    vec2 uv = (v_uv * 2.0 - 1.0);                     // -1 … +1
    uv.x *= u_resolution.x / u_resolution.y;          // preserve aspect
    float r = length(uv);                             // radial distance
    float theta = atan(uv.y, uv.x);                   // angle (-π…+π)

    /* 2. Prepare colour accumulation ------------------------------------ */
    vec3  col = vec3(0.0);
    float alpha = 0.0;                                // overall α

    /* 3. Loop over requested circles ------------------------------------ */
    int bands = clamp(u_n_circles, 0, 16);

    for (int i = 0; i < bands; ++i) {
        /* --- base radius (0.05 → 0.95) exactly as in Python ---------- */
        float baseR = mix(0.05, 0.95, float(i) / float(bands - 1));

        /* --- audio amplitude (already log-scaled & clipped) ----------- */
        float amp = u_band_amps[i];

        /* --- synthesise 'band_wave' replacement ----------------------- *
         * The Python used the *actual* waveform around the circle.
         * We approximate it with a rotating 8-petal sine for visual   *
         * richness; phase speed  = 0.6 rad/s (≈1 rev/10 s).            */
        float wave = sin(theta * 8.0 + u_time * 0.6);

        /* --- modulated radius ---------------------------------------- */
        float modR = baseR + MOD_DEPTH * amp * wave;

        /* --- draw a thin ring around modR ---------------------------- */
        float d = abs(r - modR);
        float line = smoothstep(LINE_WIDTH, 0.0, d);   // 0→1 inside line

        /* --- colour & alpha exactly like Python ---------------------- */
        vec3  bandCol = bandColour(i, bands);
        float bandAlpha = (0.1 + 0.9 * amp) * line;

        /* --- additive-over blend (cheap & close to Vispy result) ----- */
        col   = mix(col, bandCol, bandAlpha);  // simple screen-style mix
        alpha = max(alpha, bandAlpha);         // keep brightest α
    }

    fragColor = vec4(col, alpha);
}
