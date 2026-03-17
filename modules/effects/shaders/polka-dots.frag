#version 330 core

uniform vec2 u_resolution;
uniform float u_time;
uniform int u_grid_cols;
uniform int u_grid_rows;
uniform float u_dot_radius;
uniform float u_hue_shift;
uniform float u_saturation;
uniform float u_brightness;
uniform float u_edge_softness;

out vec4 fragColor;
in vec2 v_uv;

// Polka dot palette extracted from reference artwork (55 visible dots).
#define RGB(R, G, B) (vec3(float(R), float(G), float(B)) / 255.0)
const int NUM_COLORS = 55;
const vec3 palette[NUM_COLORS] = vec3[](
    RGB(138, 131, 40),
    RGB(115, 74, 119),
    RGB(220, 66, 99),
    RGB(1, 96, 90),
    RGB(0, 129, 91),
    RGB(232, 83, 3),
    RGB(1, 130, 135),
    RGB(1, 48, 118),
    RGB(206, 151, 195),
    RGB(119, 1, 15),
    RGB(183, 121, 160),
    RGB(179, 171, 1),
    RGB(1, 118, 120),
    RGB(1, 80, 149),
    RGB(63, 28, 70),
    RGB(219, 43, 5),
    RGB(202, 26, 11),
    RGB(112, 112, 112),
    RGB(188, 42, 112),
    RGB(255, 214, 0),
    RGB(214, 195, 111),
    RGB(2, 146, 91),
    RGB(34, 49, 120),
    RGB(157, 151, 1),
    RGB(2, 105, 171),
    RGB(0, 97, 130),
    RGB(27, 66, 117),
    RGB(218, 188, 6),
    RGB(252, 219, 168),
    RGB(254, 188, 2),
    RGB(227, 47, 84),
    RGB(1, 126, 180),
    RGB(122, 169, 91),
    RGB(0, 74, 45),
    RGB(218, 129, 177),
    RGB(253, 105, 51),
    RGB(12, 146, 61),
    RGB(67, 51, 96),
    RGB(148, 153, 201),
    RGB(116, 50, 51),
    RGB(130, 19, 53),
    RGB(136, 0, 2),
    RGB(121, 70, 27),
    RGB(44, 52, 28),
    RGB(1, 133, 140),
    RGB(211, 157, 193),
    RGB(7, 126, 194),
    RGB(53, 86, 85),
    RGB(212, 90, 111),
    RGB(160, 136, 0),
    RGB(42, 131, 70),
    RGB(1, 44, 95),
    RGB(2, 20, 71),
    RGB(1, 52, 21),
    RGB(188, 62, 62)
);

vec3 rgb2hsv(vec3 c) {
    vec4 K = vec4(0.0, -1.0/3.0, 2.0/3.0, -1.0);
    vec4 p = mix(vec4(c.bg, K.wz), vec4(c.gb, K.xy), step(c.b, c.g));
    vec4 q = mix(vec4(p.xyw, c.r), vec4(c.r, p.yzx), step(p.x, c.r));
    float d = q.x - min(q.w, q.y);
    float e = 1.0e-10;
    return vec3(abs(q.z + (q.w - q.y) / (6.0 * d + e)), d / (q.x + e), q.x);
}

vec3 hsv2rgb(vec3 c) {
    vec3 p = abs(fract(c.xxx + vec3(1.0, 2.0/3.0, 1.0/3.0)) * 6.0 - 3.0);
    return c.z * mix(vec3(1.0), clamp(p - 1.0, 0.0, 1.0), c.y);
}

// Simple hash for deterministic per-cell color assignment
float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

void main() {
    vec2 uv = v_uv;

    // Cell coordinates
    float cols = float(u_grid_cols);
    float rows = float(u_grid_rows);

    // Aspect-correct cell sizing
    float aspect = u_resolution.x / u_resolution.y;
    vec2 cellSize = vec2(1.0 / cols, 1.0 / rows);
    vec2 cell = floor(uv / cellSize);
    vec2 cellUV = fract(uv / cellSize);

    // Center of cell in cell-local coords (0..1)
    vec2 center = vec2(0.5);

    // Aspect correction so dots are circular
    float cellAspect = (cellSize.x * aspect) / cellSize.y;
    vec2 delta = (cellUV - center) * vec2(cellAspect, 1.0);
    float dist = length(delta);

    // Dot mask with soft edge
    float radius = u_dot_radius;
    float softness = max(u_edge_softness, 0.001);
    float dotMask = 1.0 - smoothstep(radius - softness, radius + softness, dist);

    if (dotMask < 0.001) {
        fragColor = vec4(0.0);
        return;
    }

    // Pick color from palette based on cell position
    float h = hash(cell);
    int colorIdx = int(h * float(NUM_COLORS)) % NUM_COLORS;
    vec3 color = palette[colorIdx];

    // Apply hue shift, saturation, brightness
    vec3 hsv = rgb2hsv(color);
    hsv.x = fract(hsv.x + u_hue_shift);
    hsv.y = clamp(hsv.y * u_saturation, 0.0, 1.0);
    hsv.z = clamp(hsv.z * u_brightness, 0.0, 1.0);
    color = hsv2rgb(hsv);

    fragColor = vec4(color, dotMask);
}
