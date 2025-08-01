#version 330
/*
  Broken Circles Shader
  Author: Oblique AI
  Description: Draws 5 concentric circles, each with a dent (bent corner), modulated in radius and color by the respective amplitude passed in the uniform array.
  Inputs:
    - uniform vec2 u_resolution: The resolution of the output image.
    - uniform float u_amplitudes[5]: Amplitude values for each circle (modulate radius and color).
*/

uniform vec2 u_resolution;
uniform float u_amplitudes[5];
uniform float u_time;

#define CENTER_2D vec2(0.5)

#include "lygia/draw/fill.glsl"
#include "lygia/sdf/circleSDF.glsl"
#include "lygia/draw/stroke.glsl"
#include "lygia/generative/pnoise.glsl"

out vec4 fragColor;
in  vec2 v_uv;

// Utility: draw a circle with a 'dent' (bent corner)
float dentedCircle(vec2 uv, vec2 center, float radius, float dentStrength, float dentAngle, float dentWidth) {
    // Distance from center
    float d = length(uv - center);
    // Angle from center
    float angle = atan(uv.y - center.y, uv.x - center.x);
    // Create a dent at a specific angle
    float dent = smoothstep(dentAngle - dentWidth, dentAngle + dentWidth, angle) * dentStrength * sin(8.0 * angle);
    return abs(d - (radius - dent));
}

void main() {
    // vec2 uv = v_uv * 2.0 - 1.0;                       // −1 … +1
    vec2 uv = v_uv;
    uv.x *= u_resolution.x / u_resolution.y;          // square viewport
    // Center in NDC
    vec2 center = vec2(0, 0);
    // Scale to min dimension
    float scale = min(u_resolution.x, u_resolution.y);
    vec4 color = vec4(0.0);
    float alpha = 0.0;
    
    float radius = 0;

    // make an animate-able 3D coordinate
    vec3 P = vec3(
        uv * 5.0,       // scale noise pattern
        u_time * 0.1     // animate in 3rd dimension
    );

    // periodicity of 10×10×1 units
    vec3 rep = vec3(10.0, 10.0, 1.0);

    float noise = pnoise(P, rep);


    for (int i = 0; i < 5; i++) {
        float amp = clamp(u_amplitudes[i], 0.0, 1.0);
        radius += 0.15 + 0.08 * amp;
        // float dentStrength = 0.03 + 0.07 * amp;
        // float dentAngle = 3.14159 * 0.25 * float(i); // Offset dent for each circle
        // float dentWidth = 0.3;
        float circle = circleSDF(uv);
        float stroke = stroke(circle, radius, 0.05);
        color += stroke * vec4(noise * 0.3 + 0.7 * amp, noise * 0.5 + 0.5 * amp, noise * 0.2 + 0.8 * amp, amp);
    }
    fragColor = vec4(color);
} 