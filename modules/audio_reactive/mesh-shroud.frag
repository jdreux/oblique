#version 330 core
/*  mesh_shroud.frag  ─────────────────────────────────────────────
    Generates a moving mesh-like audio shroud ribbon.
    Uniforms follow Oblique conventions.
-----------------------------------------------------------------*/
uniform vec2  u_resolution;        // viewport px
uniform float u_time;              // seconds
// uniform sampler2D u_audio_tex;     // 512×1 FFT texture (OPTIONAL)
uniform float u_fft_bands[64];
uniform float u_amp;

/* ---------------------------------------------------------------
   2-D value noise  (simple hash-based variant, no texture lookup)
   -------------------------------------------------------------*/
float hash21(vec2 p){ p = fract(p*vec2(123.34, 456.21)); 
                     p += dot(p, p+45.32); return fract(p.x*p.y); }

float vnoise(in vec2 uv){
    vec2 f = floor(uv);
    vec2 s = smoothstep(0.,1., fract(uv));
    float v00 = hash21(f);
    float v10 = hash21(f+vec2(1,0));
    float v01 = hash21(f+vec2(0,1));
    float v11 = hash21(f+vec2(1,1));
    return mix( mix(v00, v10, s.x), mix(v01, v11, s.x), s.y );
}

/* Signed distance to an antialiased line in y-direction */
float line(in vec2 p, float y, float thickness){
    float d = abs(p.y-y);
    float aa = fwidth(p.y)*.5;
    return smoothstep(thickness+aa, thickness-aa, d);
}

/* --------------------------------------------------------------*/
out vec4 fragColor;
void main(){
    // normalised screen coords centred vertically
    vec2 uv = gl_FragCoord.xy / u_resolution.xy;
    uv.x *= u_resolution.x/u_resolution.y;          // keep aspect
    vec2 p = uv * 2.-1.;                            // -1 … +1

    /* --- extract an audio envelope (optional) ----------------- */
    // float audioAmp = 30 + 0.2;

    /* --- generate N stacked "slices" to fake depth ----------- */
    const int N = 64;             // slices
    float sliceStep = 0.07;       // z-gap
    float width     = 0.003;      // line thickness

    float col = 0.0;
    for (int i=0;i<N;i++){
        float z  = i*sliceStep;                     // 0 … 1.5
        float t  = u_time*0.4 + z*1.5;              // parallax drift
        float amp = mix(0.4,1.0,smoothstep(0.,1.,z)); // wider in front

        float y =   // base sine + value noise + audio modulation
            0.15*sin(p.x*1.8 + t) +
            0.25*vnoise(vec2(p.x*2. + t, 0.0))  +
            u_fft_bands[i];

        y *= amp;
        y += mix(0.075,-0.075,z);                  // taper to centre

        col += line(p, y, width);
    }

    /* --- tone mapping ---------------------------------------- */
    col = pow(col, 0.6);             // pseudo-gamma
    fragColor = vec4(vec3(col), 1.0);
}
