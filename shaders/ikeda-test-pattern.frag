#version 330
/*
Ikeda Test Pattern Shader for Oblique
Author: AI/Oblique (adapted from ShaderToy https://www.shadertoy.com/view/MsdfWn)
Description: Generates animated Ikeda-inspired test patterns with texture input support
Inputs:
  uniform vec2 u_resolution; // Viewport resolution
  uniform float u_time; // Current time for animation
  uniform sampler2D tex0; // Input texture (optional)
*/

#ifdef GL_ES
precision mediump float;
#endif

uniform vec2 u_resolution;
uniform float u_time;
uniform sampler2D tex0;

out vec4 fragColor;
in vec2 v_uv;

void main()
{
    // sampler2D iChannel0 = tex0;
    // float iTime = u_time;
    vec2 frag = gl_FragCoord.xy;                                     
    vec2 u    = (frag / u_resolution) / vec2(1.0, 32.0);            
    vec2 speed = texture(tex0,vec2(0,u.y)).rg;
    u.x*=speed.g*.9+.1;
    u.x+=u_time*(speed.r-.5)*.3;
    fragColor=vec4((fract(texture(tex0,u).r+u_time*.5)<.5||fract(u.y*256.)<.15)?1:0);

    // /* ------------------------------------------------------------------ */
    // /* 1. Build the working UV (‘u’ in the original)                      */
    // /* ------------------------------------------------------------------ */

    // // If v_uv is already normalised 0‒1, this is exact:
    // vec2 u = vec2(v_uv.x, v_uv.y / 32.0);

    // // If, instead, you prefer to start from pixel coords do:             
    // // vec2 frag = gl_FragCoord.xy;                                     
    // // vec2 u    = (frag / u_resolution) / vec2(1.0, 8.0);              

    // // vec2 u = v_uv;

    // /* ------------------------------------------------------------------ */
    // /* 2. Read two “speed” parameters from the texture’s first column     */
    // /* ------------------------------------------------------------------ */
    // vec2 speed = texture(tex0, vec2(0.0, u.y)).rg;

    // /* Stretch X by speed.g and bias it so the scale never hits zero      */
    // u.x *= speed.g * 0.9 + 0.1;

    // /* Slide the pattern sideways; direction & rate come from speed.r     */
    // u.x += u_time * (speed.r - 0.5) * 0.3;

    // /* ------------------------------------------------------------------ */
    // /* 3. Binary test pattern                                             */
    // /* ------------------------------------------------------------------ */

    // bool cond =
    //       (fract(texture(tex0, u).r + u_time * 0.5) < 0.5)  // main stripes
    //    || (fract(u.y * 256.0)               < 0.15);        // fine scan-lines

    // fragColor = vec4(vec3(cond ? 1.0 : 0.0), 1.0);
}