#version 330
/*
iked-grid.frag
Description: Ikeda Grid - Takes a texture input and performs square swapping operations on an NxN grid.
             Inspired by Ryoji Ikeda's geometric manipulations.
Author: Oblique AI Agent
Inputs:
    - uniform sampler2D tex0; // Upstream texture to be swapped
    - uniform float u_time; // Animation time in seconds
    - uniform vec2 u_resolution; // Viewport resolution
    - uniform int u_grid_size; // NxN grid size
    - uniform float u_swap_frequency; // How often swaps occur (in Hz)
    - uniform float u_swap_phase; // Phase offset for swap timing
*/

out vec4 fragColor;

#ifdef GL_ES
precision mediump float;
#endif

uniform sampler2D tex0;
uniform float u_time;
uniform vec2 u_resolution;
uniform int u_grid_size;
uniform float u_swap_frequency;
uniform float u_swap_phase;

// Local shader parameters (not uniforms)
const int MAX_SWAPS = 8; // Maximum number of swaps active at once
const float SWAP_PATTERN_SCALE = 200.3; // Controls the pattern of swaps
const float SWAP_RANDOMNESS = 0.7; // Controls randomness in swap selection

// Pseudo-random function for generating swap patterns
float random(vec2 st) {
    // This is a classic pseudo-random hash function for GLSL:
    // 1. dot(st.xy, vec2(12.9898, 78.233)) - Creates a scalar from 2D input using magic numbers
    // 2. sin(...) * 43758.5453123 - Applies sine and scales by large constant for good distribution
    // 3. fract(...) - Returns fractional part, giving us a value in [0,1) range
    // The magic numbers are carefully chosen to avoid patterns and provide good randomness
    return fract(sin(dot(st.xy, vec2(12.9898, 78.233))) * 43758.5453123);
}

// Function to get grid cell coordinates from UV coordinates
vec2 getGridCell(vec2 uv) {
    return floor(uv * float(u_grid_size));
}

// Function to get UV coordinates within a grid cell
vec2 getCellUV(vec2 uv) {
    vec2 cell = getGridCell(uv);
    return (uv * float(u_grid_size)) - cell;
}

// Function to generate a swap pair based on time and pattern
vec4 generateSwapPair(int swapIndex, float time) {
    // Use time and swap index to generate deterministic but varied patterns
    float seed = time * SWAP_PATTERN_SCALE + float(swapIndex) * 0.5;
    
    // Generate first position
    vec2 pos1 = vec2(
        mod(random(vec2(seed, 0.0)) * float(u_grid_size), float(u_grid_size)),
        mod(random(vec2(seed, 1.0)) * float(u_grid_size), float(u_grid_size))
    );
    
    // Generate second position with some randomness
    float offsetSeed = seed + SWAP_RANDOMNESS;
    vec2 pos2 = vec2(
        mod(random(vec2(offsetSeed, 2.0)) * float(u_grid_size), float(u_grid_size)),
        mod(random(vec2(offsetSeed, 3.0)) * float(u_grid_size), float(u_grid_size))
    );
    
    // Ensure positions are different
    if (distance(pos1, pos2) < 1.0) {
        pos2 = mod(pos2 + vec2(1.0, 1.0), float(u_grid_size));
    }
    
    return vec4(pos1, pos2);
}

// Function to check if a swap should be active based on time
bool isSwapActive(int swapIndex) {
    float swapTime = u_time * u_swap_frequency + u_swap_phase;
    // Use different phases for different swaps to create varied patterns
    float phase = float(swapIndex) * 0.3;
    return mod(swapTime + phase, 2.0) > 1.0;
}

// Function to apply swap transformation to grid coordinates
vec2 applySwaps(vec2 gridCoord) {
    vec2 result = gridCoord;
    
    // Apply each swap pair if active
    for (int i = 0; i < MAX_SWAPS; i++) {
        if (isSwapActive(i)) {
            vec4 swapPair = generateSwapPair(i, u_time);
            vec2 pos1 = swapPair.xy;
            vec2 pos2 = swapPair.zw;
            
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

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution.xy;
    
    // Get the grid cell this pixel belongs to
    vec2 gridCell = getGridCell(uv);
    
    // Apply swap transformations
    vec2 swappedCell = applySwaps(gridCell);
    
    // Get UV coordinates within the cell
    vec2 cellUV = getCellUV(uv);
    
    // Calculate final coordinates for texture sampling
    vec2 finalUV = (swappedCell + cellUV) / float(u_grid_size);
    
    // Sample from the upstream texture using swapped coordinates
    vec4 texColor = texture(tex0, finalUV);
    
    // Add some visual feedback for active swaps
    float swapIntensity = 0.0;
    for (int i = 0; i < MAX_SWAPS; i++) {
        if (isSwapActive(i)) {
            vec4 swapPair = generateSwapPair(i, u_time);
            vec2 pos1 = swapPair.xy;
            vec2 pos2 = swapPair.zw;
            
            // Add subtle highlight to swapped cells
            if (gridCell == pos1 || gridCell == pos2) {
                swapIntensity += 0.05;
            }
        }
    }
    
    // Add subtle grid lines for visual reference
    bool showGrid = true; // Hardcoded variable to show/hide grid
    vec2 gridUV = uv * float(u_grid_size);
    float gridLine = step(0.95, fract(gridUV.x)) + step(0.95, fract(gridUV.y));
    gridLine = min(gridLine, 0.3); // Subtle grid lines
    
    // Combine texture color with swap highlights and grid lines
    vec3 finalColor = texColor.rgb + vec3(swapIntensity) + (showGrid ? vec3(gridLine) : vec3(0.0));
    
    fragColor = vec4(finalColor, texColor.a);
} 