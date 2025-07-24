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
    vec2 uv = v_uv * 2.0 - 1.0;                       // −1 … +1
    uv.x *= u_resolution.x / u_resolution.y;          // square viewport
    // Center in NDC
    vec2 center = vec2(0, 0);
    // Scale to min dimension
    float scale = min(u_resolution.x, u_resolution.y);
    vec3 color = vec3(0.0);
    float alpha = 0.0;
    
    float radius = 0.0;

    for (int i = 0; i < 5; ++i) {
        float amp = clamp(u_amplitudes[i]*100, 0.0, 1.0);
        radius += 0.15 + 0.08 * amp;
        float dentStrength = 0.03 + 0.07 * amp;
        float dentAngle = 3.14159 * 0.25 * float(i); // Offset dent for each circle
        float dentWidth = 0.3;
        float d = dentedCircle(uv, center, radius, dentStrength, dentAngle, dentWidth);
        float circle = 1.0 - smoothstep(0.002, 0.008, d);
        // Color modulated by amplitude
        vec3 circleColor = mix(vec3(0.2, 0.3, 0.8), vec3(1.0, 0.5 + 0.5 * amp, 0.2 + 0.8 * amp), amp);
        color += circle * circleColor * (0.5 + 0.5 * amp);
        alpha = max(alpha, circle);
    }
    fragColor = vec4(color, alpha);
} 