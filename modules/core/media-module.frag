#version 330
// Description: Renders an image texture with aspect ratio handling
// Author: AI/Oblique
// Inputs: 
//   - uniform sampler2D tex
//   - uniform ivec2 u_resolution
//   - uniform ivec2 u_img_resolution
//   - uniform int u_aspect_mode
//   - uniform vec4 u_transform (scale_x, scale_y, offset_x, offset_y)

uniform sampler2D tex;
uniform ivec2 u_resolution;
uniform ivec2 u_img_resolution;
uniform int u_aspect_mode;
uniform vec4 u_transform;

in vec2 v_uv;
out vec4 fragColor;

void main() {
    // Transform UVs according to aspect mode
    vec2 uv = v_uv;
    uv = uv * u_transform.xy + u_transform.zw;

    // Out-of-bounds handling for letterbox/preserve
    if (u_aspect_mode == 1) { // PRESERVE
        if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) {
            fragColor = vec4(0.0, 0.0, 0.0, 0.0); // transparent black bars
            return;
        }
    }
    // For COVER, just crop (no bars)
    // For FILL, just let it overflow

    fragColor = texture(tex, clamp(uv, 0.0, 1.0));
}
