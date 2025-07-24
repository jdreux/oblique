#version 330
/*
Pauric Squares Shader for Oblique
Author: AI/Oblique
Description: Generates animated square patterns with configurable size and color modes
Inputs:
  uniform vec2 u_resolution; // Viewport resolution
  uniform float u_time; // Current time for animation
*/

#include "lygia/space/sqTile.glsl";
#include "lygia/draw/fill.glsl"
#include "lygia/sdf/rectSDF.glsl"
#include "lygia/sdf/circleSDF.glsl"
#include "lygia/draw/rect.glsl"

#ifdef GL_ES
precision mediump float;
#endif

uniform vec2 u_resolution;
uniform float u_time;
uniform int u_tile_size;
out vec4 fragColor;
in vec2 v_uv;

void main()
{
  vec2 uv = v_uv;
  
  vec4 T = sqTile(uv, u_tile_size);
  vec2 localUV = T.xy;      // within [0..1] inside each little square
  vec2 ij      = T.zw;      // integer cell coords [0..7]

  vec3 color = vec3(0.0);
  float sdf = circleSDF(localUV);
  color += fill(sdf, 0.1, 0.05);

  // color+= rect(localUV, 0.1, 0.1);
  fragColor = vec4(color, 1.0);

} 