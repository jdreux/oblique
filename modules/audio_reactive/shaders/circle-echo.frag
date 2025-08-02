#version 330 core
/*
Circle Shader  – Oblique AI
Now with echo trails and no rotation.

Uniforms
--------
  u_time        Seconds since start (kept for possible future use).
  u_resolution  Viewport in pixels.
  u_n_circles   Number of primary rings (≤16).
  u_band_amps   16-element array in [0,1] (already log-scaled).

Visual constants match the Python prototype exactly.
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

/* ─── Constants lifted from visual_render_vispy.py ─────────────────────── */
const float MOD_DEPTH      = 0.08;   // radial modulation depth
const float LINE_WIDTH     = 0.0025; // visual thickness of each ring edge
const int   MAX_ECHOES     = 8;      // history depth in Python
const float ECHO_DECAY     = 0.95;   // per-echo amplitude & alpha decay
/* Gradient white → cyan (same as Python) */
const vec3  C_START = vec3(1.0);
const vec3  C_END   = vec3(0.0, 0.94, 1.0);

/* ----------------------------------------------------------------------- */
/* Linear gradient colour helper                                           */
vec3 bandColour(int i, int n)
{
    float t = (n > 1) ? float(i) / float(n - 1) : 0.0;
    return mix(C_START, C_END, t);
}

/* Smooth thin-line mask centred on radius `R`. Returns 0 … 1.             */
float ringMask(float radius, float r)
{
    float d = abs(r - radius);
    return smoothstep(LINE_WIDTH, 0.0, d);
}

/* ----------------------------------------------------------------------- */
void main()
{
    /* 1. Normalise to a centred, aspect-corrected coordinate system ----- */
    vec2 uv = v_uv * 2.0 - 1.0;                       // −1 … +1
    uv.x *= u_resolution.x / u_resolution.y;          // square viewport
    float r     = length(uv);                         // radial distance
    float theta = atan(uv.y, uv.x);                   // −π … +π

    /* 2. Accumulators for colour & alpha -------------------------------- */
    vec3  colSum = vec3(0.0);
    float alphaMax = 0.0;

    int nBands = clamp(u_n_circles, 0, 16);

    /* 3. Concentric rings ------------------------------------------------ */
    for (int band = 0; band < nBands; ++band)
    {
        /* Base radius 0.05 → 0.95 (inclusive) -------------------------- */
        float baseR = mix(0.05, 0.95, float(band) / float(nBands - 1));

        /* Pre-computed colour & amplitude ------------------------------ */
        vec3  baseColour = bandColour(band, nBands);
        float amp        = u_band_amps[band];               // 0 … 1

        /* Static eight-petal waveform around the circle  --------------- *
         *         !!  NO TIME TERM  -->   NO ROTATION  !!               */
        float wave = sin(theta * 8.0);                      // −1 … +1

        /* ----------------------------------------------------------------- */
        /* Main ring + echoes (echo 0 == main ring, echoes 1…7)              */
        /* ----------------------------------------------------------------- */
        for (int echo = 0; echo <= MAX_ECHOES; ++echo)
        {
            float decay = pow(ECHO_DECAY, float(echo));

            /* Modulation depth & line alpha decay exactly like Vispy ----- */
            float ampEcho   = amp * decay;
            float ringAlpha = (0.1 + 0.9 * ampEcho);        // pre-line mask

            /* Echoes fade harder (×½) except the primary ring ------------ */
            if (echo > 0) ringAlpha *= 0.5;

            /* Radius with reduced modulation for distant echoes ---------- */
            float modR = baseR + MOD_DEPTH * ampEcho * wave;

            /* Thin-ring mask & final per-pixel alpha --------------------- */
            float lineMask = ringMask(modR, r);
            float finalAlpha = ringAlpha * lineMask;

            /* Additive-over blend (clamp at the end) --------------------- */
            colSum   += baseColour * finalAlpha;
            alphaMax  = max(alphaMax, finalAlpha);
        }
    }

    fragColor = vec4(clamp(colSum, 0.0, 1.0), clamp(alphaMax, 0.0, 1.0));
}
