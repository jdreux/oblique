#version 330
/*
ShaderToy Tester - Fragment Shader
Author: Oblique
Description: Test shader for ShaderToy snippets
Inputs:
  uniform float iTime; // Current time in seconds
  uniform vec2 iResolution; // Viewport resolution (width, height)
  uniform vec4 iMouse; // Mouse position and click (x, y, clicked, 0)
  uniform int iFrame; // Frame number
*/

out vec4 fragColor;
in vec2 v_uv;

uniform float iTime;
uniform vec2 iResolution;
uniform vec4 iMouse;
uniform int iFrame;

void main() {
    vec2 uv = v_uv;
    vec2 fragCoord = gl_FragCoord.xy;
    
    // Default: animated gradient
    // Replace this with your ShaderToy code
    vec3 col = 0.5 + 0.5 * cos(iTime + uv.xyx + vec3(0,2,4));
    
    // Example: add some mouse interaction
    vec2 mouse = iMouse.xy / iResolution.xy;
    float dist = length(uv - mouse);
    col += vec3(0.1) * smoothstep(0.1, 0.0, dist);
    
    fragColor = vec4(col, 1.0);
} 