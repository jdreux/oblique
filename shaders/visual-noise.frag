#version 330
/*
Visual Noise Shader for Oblique
Author: AI/Oblique
Description: Generates animated visual noise with configurable size and color modes
Inputs:
  uniform vec2 u_resolution; // Viewport resolution
  uniform float u_time; // Current time for animation
  uniform float u_noise_scale; // Scale factor for noise size 
  uniform float u_intensity; // Noise intensity (0.0-1.0)
  uniform float u_color_mode; // 0.0=gray, 1.0=rgba
  uniform float u_speed; // Animation speed multiplier
*/

#ifdef GL_ES
precision mediump float;
#endif

uniform vec2 u_resolution;
uniform float u_time;
uniform float u_noise_scale;
uniform float u_color_mode;
uniform float u_speed;

out vec4 fragColor;
in vec2 v_uv;

/*  OPTIONAL: if your engine supplies iTime, keep it;
    otherwise replace the uniform with a 32-bit frame counter.         */

/*  A tiny, fast hash: returns a value in [0,1)  */
float hash(vec2 p)
{
    p  = fract(p * vec2(123.34, 345.45));   // shuffle bits
    p += dot(p, p + 34.345);
    return fract(p.x * p.y);
}

/*  Per-pixel white noise with a time-varying seed.
    ─ `frame` is an *integer* so the pattern changes abruptly each frame. */
float whiteNoise(vec2 cell, float frame)          { return hash(cell + frame); }
float whiteNoise(vec2 cell, float frame, float s) { return hash(cell + frame + s); }

void main()
{
    /* Convert the *continuous* time (seconds) to an *integer* frame index.
       60 Hz gives a convincing TV-static flicker; adjust if your swap-interval
       is different. */
    float frame = floor(u_time * 60.0 * u_speed);
    float frameSeed  = fract(sin(frame) * 43758.5453123);   // ∈ [0,1)


   /* Map the current pixel into *grain cells* of size u_noise_scale.
       Larger scale ⇒ fewer cells ⇒ coarser noise                         */
    vec2  cell   =  v_uv / u_noise_scale; // integer lattice

    /* Branch-free selection of monochrome vs RGB noise */
    float colourFlag = step(0.5, u_color_mode);           // 0 or 1

    /* Greyscale channel (always needed) */
    float n = whiteNoise(cell, frameSeed);

    /* If colourFlag==1 we compute two extra channels, otherwise reuse n */
    vec3 grain = mix(
        vec3(n),                                          // greyscale path
        vec3( n,
              whiteNoise(cell, frameSeed, 17.0),              // green ≠ red
              whiteNoise(cell, frameSeed, 42.0) ),            // blue ≠ red,green
        colourFlag);                                      // blend selector

    fragColor = vec4(grain, 1.0);    
}