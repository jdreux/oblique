#version 330
/*
Level Module Fragment Shader for Oblique
Description: Applies level adjustments (brightness, contrast, gamma, invert, black level, opacity) to input textures
Inputs:
  uniform sampler2D u_texture; // Input texture from parent module
  uniform vec2 u_resolution; // Viewport resolution
  uniform float u_time; // Current time
  uniform float u_invert; // 1.0 if invert enabled, 0.0 otherwise
  uniform float u_black_level; // Black level threshold
  uniform float u_brightness; // Brightness offset (-1 to 1)
  uniform float u_gamma; // Gamma correction
  uniform float u_contrast; // Contrast scale factor
  uniform float u_opacity; // Opacity adjustment
*/

#ifdef GL_ES
precision mediump float;
#endif

uniform sampler2D u_texture;
uniform vec2 u_resolution;
uniform float u_time;
uniform float u_invert;
uniform float u_black_level;
uniform float u_brightness;
uniform float u_gamma;
uniform float u_contrast;
uniform float u_opacity;

out vec4 fragColor;
in vec2 v_uv;

void main() {
    // Sample input texture
    vec4 color = texture(u_texture, v_uv);
    
    // Apply black level (clamp values <= threshold to black)
    if (u_black_level > 0.0) {
        vec3 luminance = vec3(0.299, 0.587, 0.114); // Standard luminance weights
        float brightness = dot(color.rgb, luminance);
        if (brightness <= u_black_level) {
            color.rgb = vec3(0.0);
        }
    }
    
    // Apply contrast (scale factor to RGB channels)
    if (u_contrast != 1.0) {
        // Contrast adjustment: scale around 0.5 (mid-gray)
        color.rgb = (color.rgb - 0.5) * u_contrast + 0.5;
    }
    
    // Apply brightness (add/subtract offset to RGB)
    if (u_brightness != 0.0) {
        color.rgb += u_brightness;
    }
    
    // Apply gamma correction
    if (u_gamma != 1.0) {
        color.rgb = pow(color.rgb, vec3(1.0 / u_gamma));
    }
    
    // Apply color inversion
    if (u_invert > 0.5) {
        color.rgb = 1.0 - color.rgb;
    }
    
    // Apply opacity adjustment
    if (u_opacity != 1.0) {
        color.a *= u_opacity;
    }
    
    // Clamp final values to valid range
    color = clamp(color, 0.0, 1.0);
    
    fragColor = color;
} 