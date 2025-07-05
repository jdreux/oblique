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
    // https://www.shadertoy.com/view/MsdfWn
    const float NUM_LINES = 128;
    vec2 frag = gl_FragCoord.xy;                                     
    vec2 u    = (frag / u_resolution) / vec2(1.0, NUM_LINES);            
    vec2 speed = texture(tex0,vec2(0,u.y)).rg;
    u.x*=speed.g*.9+.1;
    u.x+=u_time*(speed.r-.5)*.3;
    fragColor=vec4((fract(texture(tex0,u).r+u_time*.5)<.5||fract(u.y*256.)<.15)?1:0);
}