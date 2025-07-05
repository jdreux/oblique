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

uniform sampler2D tex0;
uniform float u_time;
uniform vec2 u_resolution;
uniform int u_grid_size;
uniform float u_swap_frequency;
uniform float u_swap_phase;
uniform int u_num_swaps;

in vec2 v_uv;

// Simple hash function for pseudo-random swap selection
float hash12(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
}

// Compute which two cells are swapped for a given swap index and current time
void getSwapCells(int swapIdx, out vec2 cellA, out vec2 cellB) {
    float t = floor(u_time * u_swap_frequency + float(swapIdx) + u_swap_phase);
    // Unique seeds per swap and time step
    float seedA = t + float(swapIdx) * 17.3;
    float seedB = t + float(swapIdx) * 53.1 + 1.0;
    cellA = vec2(
        floor(hash12(vec2(seedA, 1.1)) * float(u_grid_size)),
        floor(hash12(vec2(seedA, 2.3)) * float(u_grid_size))
    );
    cellB = vec2(
        floor(hash12(vec2(seedB, 7.7)) * float(u_grid_size)),
        floor(hash12(vec2(seedB, 3.9)) * float(u_grid_size))
    );

    // cellA = vec2(1.0, 3.0);  // Top-left cell
    // cellB = vec2(3.0, 3.0); 
    // Avoid swapping a cell with itself
    if (all(equal(cellA, cellB))) {
        cellB = mod(cellB + vec2(1.0, 0.0), float(u_grid_size));
    }
}

// Applies all active swaps to a given cell coordinate
vec2 applySwaps(vec2 cell) {
    // Number of concurrent swaps per frame
    vec2 current = cell;
    for (int i = 0; i < u_num_swaps; ++i) {
        vec2 a, b;
        getSwapCells(i, a, b);
        if (all(equal(current, a)))      current = b;
        else if (all(equal(current, b))) current = a;
    }
    return current;
}

void main() {
    // vec2 uv = gl_FragCoord.xy / u_resolution.xy;
    vec2 uv = v_uv;

    // Map pixel to grid cell and cell-local UV
    float N = float(u_grid_size);
    vec2 cell = floor(uv * N);
    vec2 local = fract(uv * N);

    // Apply swap operations (in cell coords)
    vec2 swappedCell = applySwaps(cell);

    // Convert back to UV for sampling
    vec2 finalUV = (swappedCell + local) / N;

    // Output color from swapped position
    // texture(tex0, finalUV) samples the input texture at the calculated UV coordinates
    // tex0: the input texture sampler (from the parent module)
    // finalUV: the UV coordinates after applying grid cell swaps
    // This creates the visual effect of swapping grid cells by sampling from different positions
    fragColor = texture(tex0, finalUV);
}