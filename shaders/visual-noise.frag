#version 330
/*
Visual Noise Shader for Oblique
Author: AI/Oblique
Description: Generates animated visual noise with configurable size and color modes
Inputs:
  uniform vec2 u_resolution; // Viewport resolution
  uniform float u_time; // Current time for animation
  uniform float u_noise_scale; // Scale factor for noise size (5.0=large, 20.0=medium, 50.0=small)
  uniform float u_intensity; // Noise intensity (0.0-1.0)
  uniform float u_color_mode; // 0.0=gray, 1.0=rgba
*/

#ifdef GL_ES
precision mediump float;
#endif

uniform vec2 u_resolution;
uniform float u_time;
uniform float u_noise_scale;
uniform float u_color_mode;

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
    float frame = floor(u_time * 60.0);

   /* Map the current pixel into *grain cells* of size u_noise_scale.
       Larger scale ⇒ fewer cells ⇒ coarser noise                         */
    vec2  cell   =  v_uv / u_noise_scale;// integer lattice

    /* Branch-free selection of monochrome vs RGB noise */
    float colourFlag = step(0.5, u_color_mode);           // 0 or 1

    /* Greyscale channel (always needed) */
    float n = whiteNoise(cell, frame);

    /* If colourFlag==1 we compute two extra channels, otherwise reuse n */
    vec3 grain = mix(
        vec3(n),                                          // greyscale path
        vec3( n,
              whiteNoise(cell, frame, 17.0),              // green ≠ red
              whiteNoise(cell, frame, 42.0) ),            // blue ≠ red,green
        colourFlag);                                      // blend selector

    fragColor = vec4(grain, 1.0);


    
}

// // Hash function for noise generation
// float hash(vec2 p) {
//     return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
// }

// // Smooth noise function
// float smoothNoise(vec2 p) {
//     vec2 i = floor(p);
//     vec2 f = fract(p);
    
//     // Smooth interpolation
//     vec2 u = f * f * (3.0 - 2.0 * f);
    
//     // Sample noise at four corners
//     float a = hash(i);
//     float b = hash(i + vec2(1.0, 0.0));
//     float c = hash(i + vec2(0.0, 1.0));
//     float d = hash(i + vec2(1.0, 1.0));
    
//     // Bilinear interpolation
//     return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
// }

// // Fractal noise with multiple octaves
// float fractalNoise(vec2 p) {
//     float value = 0.0;
//     float amplitude = 0.5;
//     float frequency = 1.0;
    
//     for (int i = 0; i < 4; i++) {
//         value += amplitude * smoothNoise(p * frequency);
//         amplitude *= 0.5;
//         frequency *= 2.0;
//     }
    
//     return value;
// }

// void main() {
//     vec2 uv = v_uv;
    
//     // Scale UV coordinates for different noise sizes
//     vec2 scaled_uv = uv * u_noise_scale;
    
//     // Add time-based animation
//     // vec2 animated_uv = scaled_uv + u_time * 0.5;
    
//     // Generate noise
//     float noise = fractalNoise(scaled_uv+u_time);
    
//     // Apply intensity
//     noise = noise * u_intensity;
    
//     // Clamp to valid range
//     noise = clamp(noise, 0.0, 1.0);
    
//     // Output color based on mode
//     if (u_color_mode > 0.5) {
//         // RGBA mode - create colorful noise
//         vec3 color = vec3(
//             fractalNoise(noise + vec2(0.0, 0.0)),
//             fractalNoise(noise + vec2(1.0, 0.0)),
//             fractalNoise(noise + vec2(0.0, 1.0))
//         );
//         color = color * u_intensity;
//         fragColor = vec4(color, 1.0);
//     } else {
//         // Gray mode - monochrome noise
//         fragColor = vec4(vec3(noise), 1.0);
//     }
// } 