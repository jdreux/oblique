#version 330 core
/*
Spectral Visualiser Shader ─ Oblique AI
Imitates the dot-matrix style shown in the reference image.
------------------------------------------------------------------
Uniforms
  u_time         (unused here – kept for possible future tweaks)
  u_resolution   viewport size in pixels
  u_bands[512]   FFT magnitudes, each ∈ [0,1]
  u_num_bands    how many bins are valid (≤512)
Inputs
  v_uv           normalised coords in [0,1]²
Output
  fragColor      RGBA
*/

#ifdef GL_ES
precision mediump float;
#endif

/* ───── uniforms ──────────────────────────────────────────────────────── */
uniform float      u_time;
uniform vec2       u_resolution;
uniform float      u_bands[512];
uniform int        u_num_bands;

/* ───── shader-side constants (tweak if you like) ─────────────────────── */
const int   DOT_ROWS = 128;              // vertical resolution of the dot grid
const float DOT_RADIUS = 0.35;           // relative radius inside one cell
const vec3  C_BOTTOM = vec3(0.00, 0.94, 1.00);  // cyan
const vec3  C_MID    = vec3(1.00);              // white
const vec3  C_TOP    = vec3(1.00, 0.40, 0.00);  // orange

/* Anti-aliased circular dot inside one cell (return 0‒1 mask) */
float dotMask(vec2 cellUV)
{
    float d = length(cellUV - 0.5);               // centre at 0.5,0.5
    // Soft edge from 0.35 → 0.45 of cell size
    return smoothstep(DOT_RADIUS + 0.10, DOT_RADIUS, d);
}

/* 3-stop vertical colour gradient: cyan → white → orange */
vec3 verticalGradient(float t)                    // t ∈ [0,1]
{
    if (t < 0.5)
        return mix(C_BOTTOM, C_MID, t * 2.0);     // 0‒0.5
    return mix(C_MID, C_TOP, (t - 0.5) * 2.0);    // 0.5‒1
}

/* ───── main ──────────────────────────────────────────────────────────── */
out vec4 fragColor;
in  vec2 v_uv;

void main()
{
    /* 1. Convert to grid coordinates ----------------------------------- */
    float columns = float(max(u_num_bands, 1));       // guard /0
    vec2  gridPos = vec2(
        v_uv.x * columns,
        v_uv.y * float(DOT_ROWS));

    ivec2 cell = ivec2(floor(gridPos));               // integer cell indices
    vec2  cellUV = fract(gridPos);                    // local 0‒1 inside cell

    /* 2. Map x cell → FFT bin index (clamp for safety) ------------------ */
    int bin = clamp(cell.x, 0, u_num_bands - 1);
    float amp = u_bands[bin];                         // 0‒1 amplitude

    /* 3. How many rows should be lit for this column? ------------------- */
    int litRows = int(amp * float(DOT_ROWS) + 0.5);   // round to nearest row
    bool lit = cell.y < litRows;

    /* 4. Build colour & alpha ------------------------------------------ */
    float dot = dotMask(cellUV);                      // smooth circular mask

    if (!lit || dot <= 0.001) {                       // quick out for speed
        fragColor = vec4(0.0);
        return;
    }

    /* Height fraction used for the gradient (0 = bottom row, 1 = top) */
    float heightT = float(cell.y) / float(DOT_ROWS - 1);
    vec3  colour  = verticalGradient(heightT);

    fragColor = vec4(colour, dot);                    // premultiplied alpha
}
