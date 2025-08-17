#version 330 core
/*
BlueBackNGray Shader – Oblique
Concentric circles with gray edges and thin borders on a white background.
Audio-reactive circles that pulse with frequency bands.

Author: AI Agent
Inputs: Band amplitudes, circle parameters

Uniforms
--------
  u_time        Seconds since start (for potential animation).
  u_resolution  Viewport in pixels.
  u_n_circles   Number of circles (≤16).
  u_mod_depth   Modulation depth for audio reactivity.
  u_band_amps   16-element array in [0,1] (log-scaled band amplitudes).
*/

#ifdef GL_ES
precision mediump float;
#endif

#include "lygia/draw/circle.glsl"

uniform float      u_time;
uniform vec2       u_resolution;
uniform int        u_n_circles;
uniform float      u_mod_depth;
uniform float      u_audio_level;

out vec4 fragColor;
in  vec2 v_uv;

/* ─── Visual Constants ──────────────────────────────────────────────────── */
const float LINE_WIDTH     = 0.003;  // thickness of circle borders
const float CIRCLE_SPACING = 0.08;   // distance between circle centers
const vec3  BACKGROUND     = vec3(1.0, 1.0, 1.0);  // white background
const vec3  CIRCLE_COLOR   = vec3(0.5, 0.5, 0.5);  // gray circles
const vec3  BORDER_COLOR   = vec3(0.3, 0.3, 0.3);  // darker gray borders




/* ─── Main Shader ───────────────────────────────────────────────────────── */
void main()
{
    vec2 uv = v_uv;
    // Start with white background
    vec3 color = BACKGROUND;
    float alpha = 1.0;
    
    int n_bands = u_n_circles;
    
    // Draw concentric circles from outside to inside
    for (int i = 0; i < n_bands; ++i)
    {
        // Calculate base radius (0.1 to 0.9)
        float base_radius = mix(0.9, 0.1, float(i) / float(max(n_bands - 1, 1)));
        // Get audio amplitude for this band
        float amp = u_audio_level * 0.8;
        
        // Modulate radius based on audio
        float modulated_radius = base_radius + u_mod_depth * amp * 0.1;
        float border = circle(uv,modulated_radius, 0.005);

        color = mix(color, BORDER_COLOR, border);
    }
    
    fragColor = vec4(color, alpha);
} 