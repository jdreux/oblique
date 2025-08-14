#version 330 core
precision highp float;

uniform sampler2D u_state;       // RGBA32F: pos.xy, vel.xy
uniform ivec2     u_tex_size;    // state texture size
uniform int       u_num_particles;

uniform vec2  u_resolution;      // framebuffer size (px)
uniform float u_point_size_px;   // base point size
uniform float u_size_speed_scale; // size multiplier based on velocity
uniform float u_softness;        // falloff exponent
uniform float u_exposure;        // tone mapping strength

out vec4 FragColor;

float softDisc(vec2 d, float rPx, float softness) {
    float r2 = dot(d, d);
    float s2 = rPx * rPx * 0.25;
    float g  = exp(-r2 / max(1e-6, (2.0*s2)));
    return pow(g, clamp(softness, 1.0, 8.0));
}

void main() {
    vec2 fragPx = gl_FragCoord.xy;
    float accum = 0.0;
    
    // Early exit for edge pixels to reduce work
    if (fragPx.x < 10.0 || fragPx.y < 10.0 || 
        fragPx.x > u_resolution.x - 10.0 || fragPx.y > u_resolution.y - 10.0) {
        FragColor = vec4(0.0, 0.0, 0.0, 1.0);
        return;
    }

    // Batch texture fetches and cull early
    int max_radius = int(u_point_size_px * 3.0); // Conservative upper bound
    
    for (int i = 0; i < u_num_particles; ++i) {
        ivec2 uv = ivec2(i % u_tex_size.x, i / u_tex_size.x);
        vec4 s   = texelFetch(u_state, uv, 0);  // pos.xy, vel.xy
        vec2 p   = s.xy;
        
        // Early spatial culling - skip if particle is too far
        vec2 d = p - fragPx;
        if (abs(d.x) > float(max_radius) || abs(d.y) > float(max_radius)) continue;
        
        vec2 v   = s.zw;
        float speed = length(v);
        float rPx   = u_point_size_px * (1.0 + u_size_speed_scale * clamp(speed/400.0, 0.0, 2.0));

        // More precise culling with actual radius
        if (abs(d.x) > rPx || abs(d.y) > rPx) continue;

        accum += softDisc(d, rPx, u_softness);
    }

    float l = 1.0 - exp(-u_exposure * accum);
    // Encode luminance in RGB so background stays black when l == 0
    FragColor = vec4(l, l, l, 1.0);
}
