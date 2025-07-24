#version 330
/*
composite.frag
Description: Blends two input textures using a selectable blend/composite operation.
Author: Oblique AI Agent
Inputs:
    uniform sampler2D tex0; // First input texture
    uniform sampler2D tex1; // Second input texture
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

uniform sampler2D tex0;
uniform sampler2D tex1;
uniform vec2 u_resolution;
uniform int u_op;

in vec2 v_uv;
out vec4 fragColor;

// Operation indices must match CompositeOp Enum order in Python
void main() {
    vec4 color0 = texture(tex0, v_uv);
    vec4 color1 = texture(tex1, v_uv);
    vec4 result = vec4(0.0);
    
    if (u_op == 0)      // ADD: Simple sum of both colors, can overflow
        result = vec4(blendAdd(color0.rgb, color1.rgb), 1.0);
    else if (u_op == 1) // AVERAGE: Mean of both colors
        result = vec4(blendAverage(color0.rgb, color1.rgb), 1.0);
    else if (u_op == 2) // MULTIPLY: Multiplies color channels, darkens
        result = vec4(blendMultiply(color0.rgb, color1.rgb), 1.0);
    else if (u_op == 3) // SCREEN: Inverse multiply, brightens
        result = vec4(blendScreen(color0.rgb, color1.rgb), 1.0);
    else if (u_op == 4) // OVERLAY: Combines multiply and screen, contrast boost
        result = vec4(blendOverlay(color0.rgb, color1.rgb), 1.0);
    else if (u_op == 5) // DIFFERENCE: Absolute difference of colors
        result = vec4(blendDifference(color0.rgb, color1.rgb), 1.0);
    else if (u_op == 6) // SUBTRACT: Subtracts color1 from color0
        result = vec4(blendSubtract(color0.rgb, color1.rgb), 1.0);
    else if (u_op == 7) // HARDLIGHT: Overlay with swapped inputs, strong contrast
        result = vec4(blendHardLight(color0.rgb, color1.rgb), 1.0);
    else if (u_op == 8) // COLORBURN: Darkens by increasing contrast
        result = vec4(blendColorBurn(color0.rgb, color1.rgb), 1.0);
    else if (u_op == 9) // COLORDODGE: Brightens by decreasing contrast
        result = vec4(blendColorDodge(color0.rgb, color1.rgb), 1.0);
    else if (u_op == 10) // HUE: Uses hue from color1, saturation/luminance from color0
        result = vec4(blendHue(color0.rgb, color1.rgb), 1.0);
    else if (u_op == 11) // COLOR: Uses color (hue/sat) from color1, luminance from color0
        result = vec4(blendColor(color0.rgb, color1.rgb), 1.0);
    else if (u_op == 12) // REFLECT: Brightens, based on reflection formula
        result = vec4(blendReflect(color0.rgb, color1.rgb), 1.0);
    else if (u_op == 13) // GLOW: Lightens, based on glow effect
        result = vec4(blendGlow(color0.rgb, color1.rgb), 1.0);
    else if (u_op == 14) // PINLIGHT: Replaces colors depending on brightness
        result = vec4(blendPinLight(color0.rgb, color1.rgb), 1.0);
    else if (u_op == 15) // EXCLUSION: Similar to difference, but lower contrast
        result = vec4(blendExclusion(color0.rgb, color1.rgb), 1.0);
    else if (u_op == 16) // NEGATION: Inverts the sum of both colors
        result = vec4(blendNegation(color0.rgb, color1.rgb), 1.0);
    else if (u_op == 17) // LINEARBURN: Subtracts and clamps, darkens
        result = vec4(blendLinearBurn(color0.rgb, color1.rgb), 1.0);
    else if (u_op == 18) // LINEARDODGE: Adds and clamps, brightens
        result = vec4(blendLinearDodge(color0.rgb, color1.rgb), 1.0);
    else if (u_op == 19) // LINEARLIGHT: Linear dodge/burn depending on color1
        result = vec4(blendLinearLight(color0.rgb, color1.rgb), 1.0);
    else if (u_op == 20) // VIVIDLIGHT: Intense contrast, combines color dodge/burn
        result = vec4(blendVividLight(color0.rgb, color1.rgb), 1.0);
    else if (u_op == 21) // HARDMIX: Posterizes to 0 or 1, high contrast
        result = vec4(blendHardMix(color0.rgb, color1.rgb), 1.0);
    else if (u_op == 22) // DARKEN: Chooses the darker of each channel
        result = vec4(blendDarken(color0.rgb, color1.rgb), 1.0);
    else if (u_op == 23) // LIGHTEN: Chooses the lighter of each channel
        result = vec4(blendLighten(color0.rgb, color1.rgb), 1.0);
    else if (u_op == 24) // PASSTHROUGH_LEFT: Passes through left texture
        result = color0;
    else if (u_op == 25) // PASSTHROUGH_RIGHT: Passes through right texture
        result = color1;
    else if (u_op == 26) // ATOP: (input1.rgba * input2.a) + (input2.rgba * (1.0 - input1.a))
        result = (color0 * color1.a) + (color1 * (1.0 - color0.a));
        result.a = 1.0;
    else result = color0;
    fragColor = clamp(result, 0.0, 1.0);
} 