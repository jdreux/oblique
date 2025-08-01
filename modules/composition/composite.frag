#version 330
/*
composite.frag
Description: Blends two input textures using a selectable blend/composite operation.
Author: Oblique AI Agent
Inputs:
    uniform sampler2D top_tex; // Top input texture
    uniform sampler2D bottom_tex; // Bottom input texture
    uniform vec2 u_resolution; // Output resolution
    uniform int u_op; // Blend/composite operation selector
*/

#ifdef GL_ES
precision mediump float;
#endif

// Lygia blend functions
#include "lygia/color/blend/add.glsl"
#include "lygia/color/blend/average.glsl"
#include "lygia/color/blend/multiply.glsl"
#include "lygia/color/blend/screen.glsl"
#include "lygia/color/blend/overlay.glsl"
#include "lygia/color/blend/difference.glsl"
#include "lygia/color/blend/subtract.glsl"
#include "lygia/color/blend/hardLight.glsl"
#include "lygia/color/blend/colorBurn.glsl"
#include "lygia/color/blend/colorDodge.glsl"
#include "lygia/color/blend/hue.glsl"
#include "lygia/color/blend/color.glsl"
#include "lygia/color/blend/reflect.glsl"
#include "lygia/color/blend/glow.glsl"
#include "lygia/color/blend/pinLight.glsl"
#include "lygia/color/blend/exclusion.glsl"
#include "lygia/color/blend/negation.glsl"
#include "lygia/color/blend/linearBurn.glsl"
#include "lygia/color/blend/linearDodge.glsl"
#include "lygia/color/blend/linearLight.glsl"
#include "lygia/color/blend/vividLight.glsl"
#include "lygia/color/blend/hardMix.glsl"
#include "lygia/color/blend/darken.glsl"
#include "lygia/color/blend/lighten.glsl"

uniform sampler2D top_tex;
uniform sampler2D bottom_tex;
uniform vec2 u_resolution;
uniform int u_op;

in vec2 v_uv;
out vec4 fragColor;

// Operation indices must match CompositeOp Enum order in Python
void main() {
    vec4 top = texture(top_tex, v_uv);
    vec4 bottom = texture(bottom_tex, v_uv);
    vec4 result = vec4(0.0);
    // 0: add, 1: average, 2: multiply, ...
    if (u_op == 0)      // ADD: Simple sum of both colors, can overflow
        result = vec4(blendAdd(top.rgb, bottom.rgb), 1.0);
    else if (u_op == 1) // AVERAGE: Mean of both colors
        result = vec4(blendAverage(top.rgb, bottom.rgb), 1.0);
    else if (u_op == 2) // MULTIPLY: Multiplies color channels, darkens
        result = vec4(blendMultiply(top.rgb, bottom.rgb), 1.0);
    else if (u_op == 3) // SCREEN: Inverse multiply, brightens
        result = vec4(blendScreen(top.rgb, bottom.rgb), 1.0);
    else if (u_op == 4) // OVERLAY: Combines multiply and screen, contrast boost
        result = vec4(blendOverlay(top.rgb, bottom.rgb), 1.0);
    else if (u_op == 5) // DIFFERENCE: Absolute difference of colors
        result = vec4(blendDifference(top.rgb, bottom.rgb), 1.0);
    else if (u_op == 6) // SUBTRACT: Subtracts bottom from top
        result = vec4(blendSubtract(top.rgb, bottom.rgb), 1.0);
    else if (u_op == 7) // HARDLIGHT: Overlay with swapped inputs, strong contrast
        result = vec4(blendHardLight(top.rgb, bottom.rgb), 1.0);
    else if (u_op == 8) // COLORBURN: Darkens by increasing contrast
        result = vec4(blendColorBurn(top.rgb, bottom.rgb), 1.0);
    else if (u_op == 9) // COLORDODGE: Brightens by decreasing contrast
        result = vec4(blendColorDodge(top.rgb, bottom.rgb), 1.0);
    else if (u_op == 10) // HUE: Uses hue from bottom, saturation/luminance from top
        result = vec4(blendHue(top.rgb, bottom.rgb), 1.0);
    else if (u_op == 11) // COLOR: Uses color (hue/sat) from bottom, luminance from top
        result = vec4(blendColor(top.rgb, bottom.rgb), 1.0);
    else if (u_op == 12) // REFLECT: Brightens, based on reflection formula
        result = vec4(blendReflect(top.rgb, bottom.rgb), 1.0);
    else if (u_op == 13) // GLOW: Lightens, based on glow effect
        result = vec4(blendGlow(top.rgb, bottom.rgb), 1.0);
    else if (u_op == 14) // PINLIGHT: Replaces colors depending on brightness
        result = vec4(blendPinLight(top.rgb, bottom.rgb), 1.0);
    else if (u_op == 15) // EXCLUSION: Similar to difference, but lower contrast
        result = vec4(blendExclusion(top.rgb, bottom.rgb), 1.0);
    else if (u_op == 16) // NEGATION: Inverts the sum of both colors
        result = vec4(blendNegation(top.rgb, bottom.rgb), 1.0);
    else if (u_op == 17) // LINEARBURN: Subtracts and clamps, darkens
        result = vec4(blendLinearBurn(top.rgb, bottom.rgb), 1.0);
    else if (u_op == 18) // LINEARDODGE: Adds and clamps, brightens
        result = vec4(blendLinearDodge(top.rgb, bottom.rgb), 1.0);
    else if (u_op == 19) // LINEARLIGHT: Linear dodge/burn depending on bottom
        result = vec4(blendLinearLight(top.rgb, bottom.rgb), 1.0);
    else if (u_op == 20) // VIVIDLIGHT: Intense contrast, combines color dodge/burn
        result = vec4(blendVividLight(top.rgb, bottom.rgb), 1.0);
    else if (u_op == 21) // HARDMIX: Posterizes to 0 or 1, high contrast
        result = vec4(blendHardMix(top.rgb, bottom.rgb), 1.0);
    else if (u_op == 22) // DARKEN: Chooses the darker of each channel
        result = vec4(blendDarken(top.rgb, bottom.rgb), 1.0);
    else if (u_op == 23) // LIGHTEN: Chooses the lighter of each channel
        result = vec4(blendLighten(top.rgb, bottom.rgb), 1.0);
    else if (u_op == 24) // PASSTHROUGH_TOP: Passes through top texture
        result = top;
    else if (u_op == 25) // PASSTHROUGH_BOTTOM: Passes through bottom texture
        result = bottom;
    else if (u_op == 26) { // ATOP: (top.rgb * bottom.a) + (bottom.rgb * (1.0 - top.a)), alpha = bottom.a
        result.rgb = (top.rgb * bottom.a) + (bottom.rgb * (1.0 - top.a));
        result.a = bottom.a;
    } else {
        result = top;
    }
    fragColor = clamp(result, 0.0, 1.0);
} 