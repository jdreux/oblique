#version 330
/*
iked-grid.frag
Description: Ikeda Grid - Creates a pattern and performs square swapping operations on an NxN grid.
             Inspired by Ryoji Ikeda's geometric manipulations.
Author: Oblique AI Agent
Inputs:
    - uniform float u_time; // Animation time in seconds
    - uniform vec2 u_resolution; // Viewport resolution
    - uniform int u_grid_size; // NxN grid size
    - uniform float u_swap_frequency; // How often swaps occur (in Hz)
    - uniform float u_swap_phase; // Phase offset for swap timing
    - uniform vec4 u_swap_pairs[16]; // Array of swap pairs (x1,y1,x2,y2) - max 16 pairs
*/

out vec4 fragColor;

#ifdef GL_ES
precision mediump float;
#endif

uniform float u_time;
uniform vec2 u_resolution;
uniform int u_grid_size;
uniform float u_swap_frequency;
uniform float u_swap_phase;
uniform vec4 u_swap_pairs[16];

// Function to get grid cell coordinates from UV coordinates
vec2 getGridCell(vec2 uv) {
    return floor(uv * float(u_grid_size));
}

// Function to get UV coordinates within a grid cell
vec2 getCellUV(vec2 uv) {
    vec2 cell = getGridCell(uv);
    return (uv * float(u_grid_size)) - cell;
}

// Function to check if a swap should be active based on time
bool isSwapActive(int pairIndex) {
    float swapTime = u_time * u_swap_frequency + u_swap_phase;
    // Use different phases for different pairs to create varied patterns
    float phase = float(pairIndex) * 0.5;
    return mod(swapTime + phase, 2.0) > 1.0;
}

// Function to apply swap transformation to grid coordinates
vec2 applySwaps(vec2 gridCoord) {
    vec2 result = gridCoord;
    
    // Apply each swap pair if active
    for (int i = 0; i < 16; i++) {
        // Check if this swap pair is valid (not zero)
        vec4 swapPair = u_swap_pairs[i];
        if (swapPair.x < 0.0) break; // Use negative x as sentinel for end of array
        
        vec2 pos1 = swapPair.xy;
        vec2 pos2 = swapPair.zw;
        
        if (isSwapActive(i)) {
            // If current position matches pos1, swap to pos2
            if (result == pos1) {
                result = pos2;
            }
            // If current position matches pos2, swap to pos1
            else if (result == pos2) {
                result = pos1;
            }
        }
    }
    
    return result;
}

// Function to generate a pattern based on coordinates and time
vec3 generatePattern(vec2 uv, float time) {
    // Create a complex pattern that will be interesting when swapped
    float x = uv.x;
    float y = uv.y;
    
    // Create multiple layers of patterns
    float pattern1 = sin(x * 20.0 + time * 2.0) * cos(y * 15.0 + time * 1.5);
    float pattern2 = sin(x * 10.0 - time * 1.0) * sin(y * 12.0 + time * 0.8);
    float pattern3 = cos(x * 8.0 + time * 0.5) * cos(y * 6.0 - time * 1.2);
    
    // Combine patterns with different weights
    float combined = pattern1 * 0.4 + pattern2 * 0.3 + pattern3 * 0.3;
    
    // Create color variations
    vec3 color1 = vec3(0.8, 0.2, 0.8); // Purple
    vec3 color2 = vec3(0.2, 0.8, 0.8); // Cyan
    vec3 color3 = vec3(0.8, 0.8, 0.2); // Yellow
    
    // Mix colors based on pattern values
    vec3 finalColor = mix(color1, color2, (combined + 1.0) * 0.5);
    finalColor = mix(finalColor, color3, abs(sin(time * 0.5)));
    
    // Add some noise for texture
    float noise = fract(sin(dot(uv, vec2(12.9898, 78.233))) * 43758.5453);
    finalColor += vec3(noise * 0.1);
    
    return finalColor;
}

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution.xy;
    
    // Get the grid cell this pixel belongs to
    vec2 gridCell = getGridCell(uv);
    
    // Apply swap transformations
    vec2 swappedCell = applySwaps(gridCell);
    
    // Get UV coordinates within the cell
    vec2 cellUV = getCellUV(uv);
    
    // Calculate final coordinates for pattern generation
    vec2 finalUV = (swappedCell + cellUV) / float(u_grid_size);
    
    // Generate a pattern based on the swapped coordinates
    vec3 patternColor = generatePattern(finalUV, u_time);
    
    // Add some visual feedback for active swaps
    float swapIntensity = 0.0;
    for (int i = 0; i < 16; i++) {
        // Check if this swap pair is valid
        vec4 swapPair = u_swap_pairs[i];
        if (swapPair.x < 0.0) break;
        
        if (isSwapActive(i)) {
            vec2 pos1 = swapPair.xy;
            vec2 pos2 = swapPair.zw;
            
            // Add subtle highlight to swapped cells
            if (gridCell == pos1 || gridCell == pos2) {
                swapIntensity += 0.1;
            }
        }
    }
    
    // Add subtle grid lines for visual reference
    vec2 gridUV = uv * float(u_grid_size);
    float gridLine = step(0.95, fract(gridUV.x)) + step(0.95, fract(gridUV.y));
    gridLine = min(gridLine, 0.3); // Subtle grid lines
    
    // Combine pattern color with swap highlights and grid lines
    vec3 finalColor = patternColor + vec3(swapIntensity) + vec3(gridLine);
    
    fragColor = vec4(finalColor, 1.0);
} 