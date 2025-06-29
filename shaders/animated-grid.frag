#version 330

/*
 * Audio-Reactive Animated Grid Shader
 * Renders an animated grid pattern that responds to audio amplitude
 * 
 * Uniforms:
 * - time: Current time in seconds
 * - resolution: Window resolution (width, height)
 * - grid_size: Number of grid cells
 * - animation_speed: Speed of animation
 * - line_width: Width of grid lines
 * - color: Grid line color (RGB)
 * - audio_intensity: Audio-reactive intensity (0-1)
 * - audio_envelope: Smoothed audio envelope
 * - audio_peak: Audio peak value
 */

uniform float time;
uniform vec2 resolution;
uniform float grid_size;
uniform float animation_speed;
uniform float line_width;
uniform vec3 color;
uniform float audio_intensity;
uniform float audio_envelope;
uniform float audio_peak;

in vec2 uv;
out vec4 fragColor;

void main() {
    // Convert UV to world coordinates
    vec2 pos = uv * resolution;
    
    // Create grid pattern
    vec2 grid = fract(pos / grid_size);
    
    // Create animated offset with audio reactivity
    float base_offset = sin(time * animation_speed) * 0.1;
    float audio_offset = audio_intensity * 0.2 * sin(time * 8.0 + pos.x * 0.01);
    grid += vec2(base_offset + audio_offset);
    
    // Calculate distance to grid lines
    vec2 dist = abs(grid - 0.5);
    float line_dist = min(dist.x, dist.y);
    
    // Create smooth lines with audio-reactive width
    float dynamic_line_width = line_width * (1.0 + audio_intensity * 2.0);
    float line = smoothstep(dynamic_line_width, 0.0, line_dist);
    
    // Add audio-reactive variation
    float audio_variation = audio_intensity * 0.3 * sin(pos.x * 0.02 + time * 4.0) * cos(pos.y * 0.02 + time * 3.0);
    line += audio_variation;
    
    // Add pulsing effect based on audio peak
    float pulse = audio_peak * 0.2 * sin(time * 20.0);
    line += pulse;
    
    // Clamp and apply color with audio intensity
    line = clamp(line, 0.0, 1.0);
    
    // Make color more vibrant when audio is loud
    vec3 dynamic_color = color * (1.0 + audio_intensity * 0.5);
    vec3 final_color = dynamic_color * line;
    
    // Add subtle background that responds to audio (using envelope for smooth response)
    vec3 background = vec3(0.05 + audio_envelope * 0.15);
    final_color += background * (1.0 - line);
    
    // Add glow effect when audio is intense
    if (audio_intensity > 0.7) {
        float glow = (audio_intensity - 0.7) * 3.33; // Normalize 0.7-1.0 to 0-1
        final_color += color * glow * 0.3;
    }
    
    fragColor = vec4(final_color, 1.0);
} 