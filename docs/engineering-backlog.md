# Oblique Engineering Backlog

Prioritized task list. Tasks are ordered by execution sequence within each sprint.

**Sources**: `docs/design-analysis.md`, `docs/creative-coding-audit.md`, `docs/ai-native-architecture.md`, `docs/ai-creative-agent-manifesto.md`

---

## Execution Sequence & Dependency Graph

```
SPRINT 1 (Week 1-2): Foundations
──────────────────────────────────
C1 ─── [IC4] Fix _resolve_param order                  (no deps, do FIRST — 1 line, unblocks C2) [DONE 2026-03-11, 8ad9269]
C2 ─── [IC4] Fix CircleEcho + audit all modules        (depends on C1) [DONE 2026-03-11, 337a7c0]
C3 ─── [IC4] Fix Uniforms TypedDicts                   (no deps, parallel with C1/C2) [DONE 2026-03-11, 67e1278]
A1 ─── [IC4] Shader error recovery                     (no deps, parallel with C1-C3) [DONE 2026-03-11, 8212b32]
B2 ─── [IC4] Add u_mix to CompositeModule              (no deps, parallel) [DONE 2026-03-11, f75cd4a]

SPRINT 2 (Week 2-3): Registry & Memory
──────────────────────────────────
A2 ─── [IC4 + Arch Review] Module registry + CLI       (no deps, but informs everything after) [DONE 2026-03-11, a40afa5]
C4 ─── [IC4] Texture cache LRU                          (no deps, parallel with A2) [DONE 2026-03-11, 98af33e]
C5 ─── [IC4] Ping-pong history eviction                 (no deps, parallel with A2) [DONE 2026-03-11, 58d3097]
C6 ─── [Sr. Architect] Standardize u_ prefix            (no deps, but easier after C2 audit) [DONE 2026-03-11, 185fcc8]

SPRINT 3 (Week 3-4): AI Feedback Loop
──────────────────────────────────
A3 ─── [IC4] Rich frame analysis                         (no deps) [DONE 2026-03-11, a748345]
A4 ─── [IC4] Param range annotations                     (depends on A2 — registry reads metadata) [DONE 2026-03-11, 7f5c9b9]
A5 ─── [IC4] Uniform contract verification               (no deps, but pairs well with A1) [DONE 2026-03-11, 53b4b85]

SPRINT 4 (Week 5-6): AI Tooling
──────────────────────────────────
A6 ─── [IC4] Shader pre-validation CLI                    (depends on A1 for fallback patterns)
A7 ─── [IC4 + Arch Review] Patch templates + oblique new  (depends on A2 — uses registry for module discovery)
D5 ─── [IC4 + Arch Review] Module scaffolding command     (depends on A2, pairs with A7)
D5
SPRINT 5 (Week 7-9): API Rework
──────────────────────────────────
B1 ─── [Sr. Architect] Remove width/height from params   (depends on A2 — registry makes it mechanical)
D6 ─── [Sr. Architect] TexturePass inheritance opt-in    (no hard dep, but do during B1 refactor) [DONE 2026-03-11, 8c60c38]

SPRINT 6 (Week 10-12): Composition API
──────────────────────────────────
B3 ─── [Sr. Architect] Pipe/chain operator                (depends on B1 + B2)

ONGOING (parallel with any sprint)
──────────────────────────────────
D1 ─── [IC4] Texture filter fix                           (no deps, quick)
D2 ─── [IC4] --profile flag                               (depends on A2 loosely)
D3 ─── [IC4] Deterministic --seed                         (no deps)
D4 ─── [IC4] A/B comparison rendering                     (depends on A3)
```

### Critical Path

The longest dependency chain is: **C1 → C2 → A2 → A4 → B1 → B3**. This is the path from "operators don't work" to "Strudel-like pipe composition". Every sprint unblocks the next.

### Seniority Guide

- **Sr. Architect (you)**: B1, B3, C6, D6 — these require design decisions about the module contract, API surface, and backward compatibility
- **IC4 Engineer**: Everything else — well-scoped, clear acceptance criteria, no ambiguous design calls

### Sprint 1 Delivery Notes (2026-03-11)

- **Completed**: C1, C2, C3, A1, B2.
- **Commit order**: `8ad9269` (C1), `337a7c0` (C2), `67e1278` (C3), `8212b32` (A1), `f75cd4a` (B2).
- **Test discipline**: full suite (`source venv/bin/activate && pytest`) run after each task commit; final state for this batch: `53 passed, 13 skipped`.

### Sprint 2 Delivery Notes (2026-03-11)

- **Completed**: A2, C4, C5, C6.
- **Commit order**: `a40afa5` (A2), `98af33e` (C4), `58d3097` (C5), `185fcc8` (C6).
- **Test discipline**: full suite (`source venv/bin/activate && pytest`) run after each task commit; final state for this batch: `62 passed, 13 skipped`.

### Sprint 3 Delivery Notes (2026-03-11)

- **Completed**: A3, A4, A5.
- **Commit order**: `a748345` (A3), `7f5c9b9` (A4), `53b4b85` (A5).
- **Test discipline**: full suite (`source venv/bin/activate && pytest`) run after each task commit; final state for this batch: `77 passed, 14 skipped`.

---

## Priority A: AI-Native Robustness & Support

These tasks make Oblique usable by an AI coding agent for patch creation, iteration, and verification.

---

### A1. Shader error recovery with last-good fallback

**Seniority**: IC4 — straightforward error handling pattern, no design ambiguity
**Sprint**: 1

**Files**: `core/renderer.py`
**Lines**: 138-145 (`render_fullscreen_quad`, around the `ctx.program()` call at line 141)

**Problem**: A GLSL compilation error in `ctx.program()` at line 141 raises `moderngl.Error` with no catch. This propagates up through the frame loop and kills the engine. An AI agent iterating on shaders crashes the entire process on every typo.

**What to do**:

1. Add a module-level `_last_good_cache: dict[str, ShaderCacheEntry] = {}` alongside the existing `_shader_cache` at line 34.
2. Wrap the `ctx.program()` call (line 141-144) in a try/except `moderngl.Error`.
3. On successful compilation, copy the entry to `_last_good_cache`.
4. On failure, if the path exists in `_last_good_cache`, log a warning and use the cached entry (program, vao, vbo). If not (first-ever compile), re-raise.
5. Add a `cleanup_last_good_cache()` function similar to the existing `cleanup_shader_cache()`.

**Test**: Write a GPU test that compiles a valid shader, then modifies the source to invalid GLSL, and verifies the renderer falls back without crashing. Also test that a first-ever bad shader still raises.

**Acceptance**: `oblique render` with a broken shader logs a warning and renders the last good frame instead of crashing.

**Status (2026-03-11)**: ✅ Complete (`8212b32`)
**Result**:

- Added `_last_good_cache` fallback behavior in `render_fullscreen_quad` and warning logs on compile failure.
- Added `cleanup_last_good_cache()` and wired cleanup into headless and engine shutdown paths.
- Added regression tests for fallback and first-compile failure behavior in `tests/core/test_renderer.py`.
**Follow-up**:
- Add a true integration test that exercises real shader compile failure on GPU (current failure path test is stub-driven).
- Consider warning-rate limiting when hot reload repeatedly retries an invalid shader.

---

### A2. Module registry with decorator and auto-discovery

**Seniority**: IC4 — implementation is mechanical, but **have Sr. Architect review the `ParamSpec`/`ModuleSpec` schema before starting** (these become the public API contract)
**Sprint**: 2
**Files**: New file `core/registry.py`, modifications to `cli.py`

**What to do**:

1. Create `core/registry.py` with:
  - A `ParamSpec` dataclass: `name: str`, `type: str`, `default: Any`, `min: float | None`, `max: float | None`, `description: str`, `semantic: str`
  - A `ModuleSpec` dataclass: `name: str`, `category: str`, `description: str`, `tags: list[str]`, `params: list[ParamSpec]`, `inputs: list[str]`, `outputs: list[str]`, `cost_hint: str`, `shader_path: str`, `module_class: str`
  - A global `_registry: dict[str, ModuleSpec] = {}`
  - An `@oblique_module(category, description, tags, cost_hint)` decorator that registers a class in `_registry`
  - A `_extract_params(cls)` function that reads `dataclasses.fields()` from the module's Params dataclass (via `__orig_bases__` generic args) and builds `ParamSpec` list. Skip `width` and `height` fields.
  - A `discover_modules()` function using `pkgutil.walk_packages()` on the `modules` package to auto-import all module files, triggering decorators.
  - A `get_registry() -> dict[str, ModuleSpec]` function.
  - A `search_modules(query, tags, category) -> list[ModuleSpec]` function doing keyword match on name + description + tags.
2. Add the `@oblique_module` decorator to all 23 module classes. For each module, provide:
  - `category`: match the directory (`audio_reactive`, `effects`, `core`, `composition`, `utility`)
  - `description`: 1-2 sentence description of what it does visually
  - `tags`: 3-5 tags from this taxonomy: `geometric | organic | glitch | minimal | dense | noisy | clean | static | pulsing | flowing | chaotic | rhythmic | evolving | audio-reactive | beat-sync | frequency-split | amplitude | monochrome | colorful | dark | bright | neon | muted | distortion | feedback | blur | composite | transform | particle`
  - `cost_hint`: `"low"`, `"medium"`, or `"high"` (based on shader complexity — SDF modules like protoplasm are high, simple passthrough like feedback is low)
3. Add CLI commands to `cli.py`:
  - `oblique list-modules` — tabular output: name, category, description
  - `oblique list-modules --json` — full `ModuleSpec` as JSON array
  - `oblique list-modules --tag <tag>` — filter by tag
  - `oblique list-modules --category <category>` — filter by category
  - `oblique describe <ModuleName>` — full detail for one module
  - `oblique describe <ModuleName> --json` — JSON output

**Test**: Unit test that `discover_modules()` finds all module classes, that `get_registry()` returns correct counts, that `search_modules("feedback")` finds `FeedbackModule`, that `--json` output is valid JSON matching `ModuleSpec` schema.

**Acceptance**: `oblique list-modules --json` returns structured metadata for all modules. An AI agent can parse this JSON to discover available modules, their params, ranges, and tags without reading any source files.

**Status (2026-03-11)**: ✅ Complete (`a40afa5`)
**Result**:

- Added `core/registry.py` with `ParamSpec`, `ModuleSpec`, decorator-based registration, module discovery, and search helpers.
- Decorated all current `BaseAVModule` subclasses (22 modules) with category/description/tags/cost metadata.
- Added CLI commands: `oblique list-modules` (table/JSON with tag+category filters) and `oblique describe <ModuleName>` (text/JSON detail).
- Added tests covering registry discovery/search/serialization and parser/CLI command behavior.
**Follow-up**:
- Add Sr. Architect review pass for tag taxonomy consistency and `cost_hint` calibration.
- Consider a stricter schema validator for `ModuleSpec` JSON output to lock API stability before public tooling relies on it.

---

### A3. Rich frame analysis in headless renderer

**Seniority**: IC4 — pure numpy math, well-defined output contract
**Sprint**: 3
**Files**: New file `core/frame_analysis.py`, modifications to `core/headless_renderer.py` and `cli.py`

**What to do**:

1. Create `core/frame_analysis.py` with pure-numpy implementations (no scipy, no opencv):
  - `analyze_frame(arr: np.ndarray) -> dict` where `arr` is (H, W, 4) float32 RGBA [0,1]. Returns:
    - `mean_brightness`, `brightness_std` (luminance: 0.2126R + 0.7152G + 0.0722B)
    - `non_black_ratio` (luminance > 0.01), `clipped_ratio` (luminance > 0.99)
    - `mean_color_rgb` (3-element list)
    - `color_variance` (mean of per-channel variance)
    - `mean_saturation` (from HSV: delta/max)
    - `dominant_hue` (string from 12-bin hue histogram: "red", "orange", "yellow", "chartreuse", "green", "spring", "cyan", "azure", "blue", "violet", "magenta", "rose", or "achromatic" if low saturation)
    - `edge_density` (mean of Sobel-like gradient: `abs(img[:, 2:] - img[:, :-2])`)
    - `spatial_balance` (1.0 - (max quadrant brightness - min quadrant brightness))
    - `center_brightness`, `edge_brightness` (center = radius < 0.3, edge = radius > 0.7)
    - `is_blank` (mean_brightness < 0.005), `is_saturated` (clipped_ratio > 0.5), `is_dark` (mean_brightness < 0.1), `has_color` (mean_saturation > 0.1)
  - `analyze_temporal(frames: list[np.ndarray]) -> dict` — for 2+ frames:
    - `mean_motion` (mean of frame-to-frame RGB abs diff), `motion_variance`, `peak_motion`
    - `is_static` (mean_motion < 0.001), `is_chaotic` (motion_variance > 0.01)
    - `motion_profile` (list of per-transition motion values)
  - `perceptual_hash(arr: np.ndarray, hash_size=8) -> str` — downsample to 8x8 grayscale, compare each pixel to mean, return bitstring
  - `hash_distance(h1: str, h2: str) -> int` — Hamming distance
2. Update `HeadlessRenderer.inspect(t)` to use `analyze_frame()` instead of the current 2-metric implementation.
3. Add `HeadlessRenderer.inspect_sequence(times: list[float]) -> dict` that renders multiple frames, returns `analyze_frame()` for the last frame plus `analyze_temporal()` for all frames.
4. Update `cli.py` render command: when `--inspect` is used with `--duration` or `--frames`, output temporal analysis too.

**Test**: Unit tests for `analyze_frame` with synthetic arrays (all-black, all-white, half-red-half-blue, gradient). Test `analyze_temporal` with identical frames (static) and different frames (motion). Test `perceptual_hash` returns consistent results for same input.

**Acceptance**: `oblique render <patch> --t 1.0 --inspect` outputs 16+ metrics as JSON. `oblique render <patch> --duration 2 --fps 5 --inspect` adds temporal analysis.

**Status (2026-03-11)**: ✅ Complete (`a748345`)
**Result**:

- Added new `core/frame_analysis.py` with `analyze_frame`, `analyze_temporal`, `perceptual_hash`, and `hash_distance` (pure NumPy).
- Updated `HeadlessRenderer.inspect()` to emit rich metrics and added `HeadlessRenderer.inspect_sequence()` with temporal motion metrics.
- Updated `oblique render --inspect` to print JSON and include temporal analysis when used with `--duration` or `--frames`.
- Added tests for synthetic frame analysis cases, temporal analysis behavior, headless inspect coverage, and CLI inspect JSON/timeline behavior.
**Follow-up**:
- Consider exposing perceptual hash in CLI `--inspect` output for snapshot similarity checks.
- Consider adding optional histogram metrics (luminance and hue bins) for deeper agent-side diagnostics.

---

### A4. Parameter range annotations on all modules

**Seniority**: IC4 — mechanical work, but requires reading each shader to determine valid ranges. Time-consuming but no design decisions.
**Sprint**: 3 (depends on A2)
**Files**: All `*Params` dataclasses across `modules/`

**What to do**:

1. Add `metadata` dict to each `dataclasses.field()` with keys: `min`, `max`, `description`. For example:
  ```python
   feedback_strength: ParamFloat = field(
       default=0.97,
       metadata={"min": 0.0, "max": 1.0, "description": "Per-frame decay. 0=no trail, 1=infinite"}
   )
  ```
2. Update `_extract_params` in `core/registry.py` to read `field.metadata` and populate `ParamSpec.min`, `ParamSpec.max`, `ParamSpec.description`.
3. Annotate all params across these modules (reference the shader source for valid ranges):
  **core**: `VisualNoiseModule` (noise_size, color_mode, intensity, speed), `MediaModule`
   **audio_reactive**: `CircleEcho` (n_circles, mod_depth, audio_level), `RyojiLines` (num_bands + any others), `SpectralVisualizer`, `MITParticles`, `Protoplasm`, `GridSwap`, `PauricSquares`, `BrokenCircles`, `BluBackNGray`, `IkedaTestPattern`, `IkedaTinyBarcode`, `MeshShroud`
   **effects**: `FeedbackModule` (feedback_strength, direction), `BlurModule` (blur_amount, kernel_size), `BarrelDistortion` (strength), `LevelModule` (brightness, contrast, etc.)
   **composition**: `CompositeModule` (operation)
   **utility**: `Transform` (scale, rotation, translation), `Debug`, `ShadertoyImporter`
4. For enum-like params (noise_size, color_mode, operation), use `metadata={"enum_values": ["small", "medium", "large"]}`.

**Test**: For each annotated module, verify `get_registry()[ModuleName].params` contains non-None min/max/description for all numeric params.

**Acceptance**: `oblique describe FeedbackModule --json` shows param ranges and descriptions. An AI agent knows that `feedback_strength` is 0.0-1.0 without reading source.

**Status (2026-03-11)**: ✅ Complete (`7f5c9b9`)
**Result**:

- Added `field(metadata=...)` annotations with `min`/`max`/`description` across the targeted `*Params` dataclasses in `modules/`.
- Added enum metadata for enum-like params (`noise_size`, `color_mode`, `operation`, plus related enum/string controls such as `aspect_mode` and `transform_order`).
- Extended `ParamSpec` extraction in `core/registry.py` to preserve `enum_values` in registry output.
- Added registry tests to verify numeric params in annotated modules expose ranges/descriptions and that enum metadata survives discovery.
**Follow-up**:
- Add a schema-level distinction for scalar ranges vs vector/tuple ranges (current `min`/`max` are shared bounds).
- Schedule a pass to align param bounds with creative presets used in real-time patches.

---

### A5. Uniform contract verification (debug mode)

**Seniority**: IC4 — straightforward set comparison, no design ambiguity
**Sprint**: 3
**Files**: `core/renderer.py`
**Lines**: 157-188 (the uniform-setting loop in `render_fullscreen_quad`)

**What to do**:

1. Add a module-level `_debug_mode: bool = False` and a `set_debug_mode(enabled: bool)` function.
2. After shader compilation succeeds and before the uniform loop, if `_debug_mode`:
  - Get the set of uniform names from the compiled program (moderngl `Program` supports `__contains_`_ and iteration).
  - Get the set of provided uniform keys.
  - Compute `extra = provided - shader_uniforms` and `missing = shader_uniforms - provided - {"in_vert", "in_uv"}` (exclude vertex attributes).
  - If `extra`: `logger.warning(f"[{frag_shader_path}] Python provides but shader ignores: {extra}")`.
  - If `missing`: `logger.warning(f"[{frag_shader_path}] Shader expects but Python doesn't provide: {missing}")`.
3. Add `--debug` flag to `oblique render` and `oblique start` CLI commands that calls `set_debug_mode(True)`.

**Test**: Create a module with a deliberate uniform mismatch (Python sends `u_brightnes`, shader expects `u_brightness`). Run in debug mode and verify warning is logged.

**Acceptance**: `oblique render <patch> --t 1.0 --debug` logs any uniform mismatches between Python and GLSL.

**Status (2026-03-11)**: ✅ Complete (`53b4b85`)
**Result**:

- Added renderer debug mode (`_debug_mode`, `set_debug_mode`) and uniform contract validation in `render_fullscreen_quad`.
- Debug mode now logs both extra provided uniforms and missing expected shader uniforms (excluding `in_vert`/`in_uv`).
- Added `--debug` flags to both `oblique start` and `oblique render` and wired them to renderer debug mode.
- Added tests covering renderer mismatch warning behavior and CLI parser/runtime debug wiring.
**Follow-up**:
- Add rate-limiting/deduplication for repeated mismatch warnings during shader hot reload.
- Include optional uniform type/shape details in debug warnings to catch value-shape issues, not just missing keys.

---

### A6. Shader pre-validation via CLI

**Seniority**: IC4 — wraps existing preprocessor + moderngl compile, no design calls
**Sprint**: 4 (depends on A1)
**Files**: New file `core/shader_validator.py`, modifications to `cli.py`

**What to do**:

1. Create `core/shader_validator.py` with:
  - `validate_shader(shader_path: str) -> dict` that:
   a. Runs the shader preprocessor (`core/shader_preprocessor.py`) to resolve `#include` directives
   b. Creates a standalone moderngl context
   c. Attempts to compile the preprocessed fragment shader with a minimal vertex shader
   d. Returns `{"valid": True, "uniforms": [...]}` on success
   e. Returns `{"valid": False, "error": str, "uniforms": []}` on failure
   f. Always releases the context
  - `validate_patch_shaders(patch_module: str) -> list[dict]` that discovers all `.frag` files used by a patch's modules and validates each one.
2. Add `oblique validate <patch_module>` CLI command that:
  - Imports the patch module
  - Runs `validate_patch_shaders` on all shaders involved
  - Prints pass/fail per shader with error details
  - Exit code 0 if all pass, 1 if any fail

**Test**: Validate a known-good shader (should pass). Validate a shader with a syntax error (should fail with error message). Validate a shader with `#include` directives (preprocessor should resolve them).

**Acceptance**: `oblique validate projects.demo.demo_audio_file` reports pass/fail for each shader used by the patch.

---

### A7. Patch templates and `oblique new` CLI command

**Seniority**: IC4 — string templating, but **have Sr. Architect review template choices** (these become the "golden path" for new users and AI agents)
**Sprint**: 4 (depends on A2)
**Files**: New directory `templates/`, modifications to `cli.py`

**What to do**:

1. Create `templates/` directory with these Python template files:
  - `audio_reactive.py` — AudioFileInput + FFTBands + one configurable visual module + optional FeedbackModule
  - `feedback_loop.py` — VisualNoise + FeedbackModule + optional BarrelDistortion
  - `layered_composite.py` — Two visual modules + CompositeModule with configurable blend mode
  - `blank_canvas.py` — Single VisualNoiseModule, no audio, minimal
   Each template is a function that takes keyword args and returns a string of Python source code (the patch file contents). Use string formatting, not AST manipulation.
2. Add `oblique new <template_name>` CLI command with flags:
  - `--audio <path>` — audio file path (for audio_reactive template)
  - `--module <ModuleName>` — primary visual module (default varies by template)
  - `--feedback` — include feedback module (boolean flag)
  - `--blend <mode>` — blend mode for layered template (default: "screen")
  - `--output <path>` — where to write the generated patch file (default: stdout)
3. Add `oblique templates` — list available templates with descriptions.

**Test**: Generate each template, verify the output is valid Python that imports correctly. Verify `--audio` flag is reflected in the generated AudioFileInput path.

**Acceptance**: `oblique new audio-reactive --audio track.wav --module CircleEcho --feedback --output my_patch.py` generates a runnable patch file.

---

## Priority B: Major API Reworks

These are structural changes that improve the composition model and developer experience.

---

 -- 
**Seniority**: Sr. Architect — changes the `prepare_uniforms` method signature across the entire module contract. Requires design decision on how resolution flows through the system. IC4 can execute stages 2-4 after the architect lands stage 1.
**Sprint**: 5 (depends on A2)
**Files**: `modules/core/base_av_module.py` (BaseAVParams), all 23 module files, all demo patches in `projects/`, all tests

**Problem**: Every `*Params` dataclass has `width: int` and `height: int` from `BaseAVParams`. Every module constructor requires them. Every patch threads them through every instantiation. But `render_texture(ctx, width, height, t)` already passes resolution at render time. The params are redundant.

**What to do**:

1. Remove `width` and `height` from `BaseAVParams` in `base_av_module.py`.
2. In `prepare_uniforms`, any module that references `self.params.width` or `self.params.height` must instead receive width/height as a method argument. Change `prepare_uniforms(self, t: float)` signature to `prepare_uniforms(self, t: float, width: int, height: int)` across all modules. Update the call site in `render_texture()` to pass width/height.
3. Update all `*Params` dataclasses to remove `width`/`height`.
4. Update all patch files in `projects/` to stop passing width/height to module constructors.
5. Update all tests.

**NOTE**: This is a large refactor touching every module. Do it in stages:

- Stage 1: Add `width`/`height` as optional params to `prepare_uniforms` alongside the existing params, with fallback to `self.params.width`. This keeps backward compatibility.
- Stage 2: Migrate all modules to use the method args instead of `self.params.width`.
- Stage 3: Remove `width`/`height` from `BaseAVParams`.
- Stage 4: Clean up all patches and tests.

**Depends on**: A2 (registry makes it mechanical to find all modules and their params)

**Test**: All existing tests pass after each stage. Headless renderer produces identical output at 800x600 before and after. A patch rendered at 800x600 then at 1920x1080 produces correctly scaled output.

**Acceptance**: No module constructor takes `width` or `height`. Patches are resolution-independent.

---

### B2. Add `u_mix` crossfade to CompositeModule

**Seniority**: IC4 — one param, one uniform, one GLSL line. Clear spec.
**Sprint**: 1 (no deps, quick win)
**Files**: `modules/composition/composite_module.py`, `modules/composition/shaders/composite.frag`

**Problem**: `CompositeModule` blends two textures with a blend mode (`CompositeOp` enum, 27 modes) but has no mix/opacity parameter. You can't crossfade between two scenes.

**What to do**:

1. Add `mix: ParamFloat = 1.0` to `CompositeParams` with `metadata={"min": 0.0, "max": 1.0, "description": "Blend amount. 0.0=bottom only, 1.0=full blend"}`.
2. Add `u_mix: float` to `CompositeUniforms`.
3. In `prepare_uniforms`, resolve `mix` via `_resolve_param` and add to uniforms dict.
4. In `composite.frag`, after computing the blended result, apply: `result = mix(bottom_color, blended_color, u_mix);`
5. When `u_mix` is 0.0, output is pure bottom texture. When 1.0, output is the full composite operation. Values between interpolate linearly.

**Test**: Render with `u_mix=0.0` → output matches bottom texture. `u_mix=1.0` → output matches current behavior. `u_mix=0.5` → output is intermediate.

**Acceptance**: `CompositeModule` supports smooth crossfading between two visual sources.

**Status (2026-03-11)**: ✅ Complete (`f75cd4a`)
**Result**:

- Added `mix` param with metadata to `CompositeParams`, plus `u_mix` in `CompositeUniforms`.
- Updated `prepare_uniforms` to resolve dynamic `mix` values via `_resolve_param`.
- Updated GLSL to apply `result = mix(bottom, result, u_mix);`.
- Added module + shader coverage tests in `tests/modules/test_composite_module_mix.py`.
**Follow-up**:
- Add image-based render assertions for `u_mix` at 0.0 / 0.5 / 1.0 once a stable GPU integration harness is in place.

---

### B3. Pipe/chain operator on BaseAVModule

**Seniority**: Sr. Architect — defines a new composition API on the base class. Requires design decisions about lazy vs eager instantiation, how `input_texture` wiring works generically, and how `.mix()` interacts with `CompositeOp`. IC4 can implement after the architect writes the `ModuleChain` skeleton and API tests.
**Sprint**: 6 (depends on B1 + B2)
**Files**: `modules/core/base_av_module.py`, new file `core/module_chain.py`

**Problem**: Composing modules requires nested constructors read inside-out. An AI agent building `noise → feedback → distortion → composite` must write the chain backwards.

**What to do**:

1. Create `core/module_chain.py` with a `ModuleChain` class:
  ```python
   class ModuleChain:
       def __init__(self, source: BaseAVModule):
           self._chain: list[tuple[type, dict]] = []
           self._source = source

       def pipe(self, module_cls_or_instance, **params) -> "ModuleChain":
           # If instance, just append. If class+params, store for lazy instantiation.
           ...
           return self

       def mix(self, other: BaseAVModule, amount: float = 0.5, op: CompositeOp = CompositeOp.SCREEN) -> "ModuleChain":
           # Wraps in CompositeModule with u_mix
           ...
           return self

       def build(self) -> BaseAVModule:
           # Materialize the chain: instantiate modules, wire input_texture params
           ...
  ```
2. Add a `.pipe()` method to `BaseAVModule` that creates a `ModuleChain`:
  ```python
   def pipe(self, effect_cls_or_instance, **params) -> ModuleChain:
       return ModuleChain(self).pipe(effect_cls_or_instance, **params)
  ```
3. The chain must handle `input_texture` wiring automatically — each piped module gets the previous module as its `input_texture`.

**Test**: Build a chain `VisualNoise().pipe(FeedbackModule, feedback_strength=0.9).pipe(BarrelDistortion, strength=0.5).build()` and verify it renders correctly via headless renderer.

**Acceptance**: Modules can be composed with `.pipe()` and `.mix()` in a left-to-right readable chain.

---

## Priority C: Bug Fixes & Leaky Abstractions

These are correctness issues identified in the design analysis.

---

### C1. Fix `_resolve_param` check order

**Seniority**: IC4 — 1-line swap, clear before/after
**Sprint**: 1 (do FIRST — unblocks C2)
**File**: `modules/core/base_av_module.py`
**Lines**: 388-391

**Problem**: `isinstance(param, Callable)` is checked before `isinstance(param, BaseProcessingOperator)`. Since `BaseProcessingOperator` subclasses may be callable, the operator branch at line 390-391 is dead code. Operators get `param()` called instead of `param.process()`.

**What to do**: Swap the order — check `BaseProcessingOperator` first:

```python
if isinstance(param, BaseProcessingOperator):
    return param.process()
elif isinstance(param, Callable):
    return param()
else:
    return param
```

**Test**: Create a mock `BaseProcessingOperator` subclass with both `__call__` and `process()` returning different values. Pass it to `_resolve_param`. Verify `process()` is called, not `__call__`.

**Acceptance**: `_resolve_param` correctly calls `.process()` on processing operators.

**Status (2026-03-11)**: ✅ Complete (`8ad9269`)
**Result**:

- Swapped `_resolve_param` type-check order so `BaseProcessingOperator` resolves before generic callables.
- Added regression test with a callable processing operator to ensure `.process()` takes precedence.
**Follow-up**:
- Keep this regression test as a guard during B1 API refactor where param resolution paths will be touched again.

---

### C2. Fix CircleEcho to use `_resolve_param`

**Seniority**: IC4 — mechanical, but the "audit all modules" part is thorough work. Follow the pattern, check every module.
**Sprint**: 1 (depends on C1)
**File**: `modules/audio_reactive/circle_echo.py`
**Lines**: `prepare_uniforms` method

**Problem**: `prepare_uniforms` reads `self.params.n_circles`, `self.params.mod_depth`, `self.params.audio_level` directly without calling `_resolve_param()`. This means lambdas and processing operators passed as param values are sent as raw objects to the shader, causing runtime errors or silent failures.

**What to do**: Wrap each param access in `_resolve_param`:

```python
"u_n_circles": self._resolve_param(self.params.n_circles),
"u_mod_depth": self._resolve_param(self.params.mod_depth),
"u_audio_level": self._resolve_param(self.params.audio_level),
```

Also do `self._resolve_param(self.params.width)` and `self._resolve_param(self.params.height)` for resolution (or use the method arg after B1).

**Audit other modules**: Check ALL modules' `prepare_uniforms` for direct param access without `_resolve_param`. Known issue in CircleEcho but may exist elsewhere. Module list:

- `blue_back_n_gray.py`
- `broken_circles.py`
- `grid_swap_module.py`
- `ikeda_test_pattern.py`
- `ikeda_tiny_barcode.py`
- `mesh_shroud.py`
- `mit_particles.py`
- `pauric_squares_module.py`
- `protoplasm.py`
- `spectral_visualizer.py`

**Test**: Pass a lambda as `n_circles` to CircleEcho, render a frame, verify the lambda is called and the integer value reaches the shader.

**Acceptance**: All `ParamX` fields in all modules go through `_resolve_param` before being sent to the shader.

**Status (2026-03-11)**: ✅ Complete (`337a7c0`)
**Result**:

- Fixed `CircleEcho.prepare_uniforms()` to resolve width/height + dynamic params through `_resolve_param`.
- Audit identified another direct dynamic-param bypass in `SpectralVisualizer`; fixed in same pass.
- Added coverage tests for callable param resolution in both modules (`tests/modules/test_audio_reactive_param_resolution.py`).
**Follow-up**:
- Re-run this audit after B1 (`width`/`height` contract refactor), since every `prepare_uniforms` implementation will be edited.

---

### C3. Fix `*Uniforms` TypedDicts to use correct types

**Seniority**: IC4 — type annotation fix, no runtime behavior change
**Sprint**: 1 (no deps, parallel with C1/C2)
**Files**: `modules/composition/composite_module.py`, `modules/effects/feedback.py`, check `modules/utility/transform.py`

**Problem**: Texture uniform fields are typed as `BaseAVModule` or `ParamTexture` instead of `moderngl.Texture`. This works incidentally because `TexturePass` routing resolves them, but the types are misleading for anyone writing new modules.

**What to do**:

1. In `composite_module.py` lines 52-55, change:
  ```python
   top_tex: BaseAVModule      # wrong
   bottom_tex: BaseAVModule   # wrong
  ```
   to:
2. In `feedback.py` line 20, change:
  ```python
   u_input_texture: ParamTexture   # wrong
  ```
   to:
3. Check `transform.py` and any other module with texture uniforms for the same issue.
4. NOTE: These TypedDicts are documentation, not enforced at runtime. The change is for correctness of the type contract.

**Test**: Type-check with mypy or pyright if configured. Otherwise, visual review.

**Acceptance**: All `*Uniforms` TypedDicts accurately reflect what the renderer expects (moderngl types, not Python wrapper types).

**Status (2026-03-11)**: ✅ Complete (`67e1278`)
**Result**:

- Updated texture uniform annotations to `moderngl.Texture` in `composite`, `feedback`, and audited additional modules (`transform`, `blur`, `level`, `barrel_distortion`, `grid_swap`, `pauric_squares`).
- Added annotation-level regression test in `tests/modules/test_uniform_texture_types.py`.
**Follow-up**:
- Run mypy/pyright once strict static type checking is introduced to enforce these contracts automatically.

---

### C4. Texture cache LRU eviction

**Seniority**: IC4 — standard LRU pattern, clear cap
**Sprint**: 2 (no deps, parallel with A2)
**File**: `core/renderer.py`
**Line**: 35 (`_texture_cache: dict[str, moderngl.Texture] = {}`)

**Problem**: `_texture_cache` grows unbounded. Each unique `cache_tag` creates a permanent GPU allocation. Long-running sessions accumulate dead textures.

**What to do**:

1. Replace `dict` with an `OrderedDict` (or use a simple LRU approach).
2. After inserting a new entry, if `len(_texture_cache) > 64`, evict the oldest entry and call `.release()` on the texture.
3. Same treatment for `_texture_history` — cap at 2 entries per `(pass_tag, width, height)` key prefix.

**Test**: Create 100 textures via the cache, verify only 64 remain. Verify evicted textures are released (mock `.release()` and check call count).

**Acceptance**: `_texture_cache` never exceeds 64 entries. GPU memory stays bounded.

**Status (2026-03-11)**: ✅ Complete (`98af33e`)
**Result**:

- Migrated `_texture_cache` to `OrderedDict` LRU semantics in `core/renderer.py`.
- Added hard cap (`64`) with eviction of oldest entries and explicit texture release on eviction.
- Added regression test verifying cache capacity enforcement and release order.
**Follow-up**:
- Expose cache cap via config/env if runtime workloads need tuning beyond 64 entries.

---

### C5. Ping-pong history eviction

**Seniority**: IC4 — requires understanding the ping-pong buffer lifecycle, but well-scoped
**Sprint**: 2 (no deps, parallel with C4)
**File**: `modules/core/base_av_module.py`
**Variable**: `_texture_history` (class-level or module-level dict)

**Problem**: `_texture_history` keys encode `frame_index % 2` but old entries from different resolutions or pass tags are never evicted. Hours of running = dead GPU allocations.

**What to do**:

1. Find the `_texture_history` dict (likely in `base_av_module.py` or `renderer.py`).
2. Key structure should be `(pass_tag, width, height, frame_index % 2)`.
3. After writing a new entry, scan for entries with the same `(pass_tag)` but different `(width, height)` — release and remove them.
4. Alternatively, keep a max of 4 entries per `pass_tag` (2 ping-pong × current resolution).

**Test**: Render at 800x600, then at 1920x1080. Verify old 800x600 entries are evicted from history.

**Acceptance**: `_texture_history` stays bounded. No stale-resolution textures accumulate.

**Status (2026-03-11)**: ✅ Complete (`58d3097`)
**Result**:

- Added ping-pong history eviction in `BaseAVModule` scoped by `(owner, pass_tag, resolution)`.
- On resolution change, stale-history textures are removed and released via renderer cache-aware release helper.
- Added safety cap to keep at most 4 history entries per pass/resolution bucket.
- Added regression test that renders at one resolution then another and verifies stale entries are evicted/released.
**Follow-up**:
- Add metrics/log hooks for eviction counts to make long-session memory behavior observable in profiling runs.

---

### C6. Standardize `u_` prefix convention

**Seniority**: Sr. Architect — this is a convention change that affects every module and all future module authoring. The architect should decide the convention and update the renderer; IC4 can do the mechanical migration across all modules.
**Sprint**: 2 (no hard deps, but easier after C2 audit)
**Files**: `core/renderer.py` (auto-prefix logic in `_render_texture_pass`), all module `prepare_uniforms` methods

**Problem**: `_render_texture_pass` auto-adds `u_` to `TexturePass.uniforms` keys, but `prepare_uniforms()` output passes through raw. `CompositeModule` mixes `"top_tex"` (no prefix) with `"u_op"` (with prefix) in the same dict. An AI cannot determine the naming rule.

**What to do**: Pick ONE convention and enforce it everywhere. Recommended: **always require explicit `u_` prefix in Python code, remove the auto-prefix logic.**

1. In `renderer.py`, find the code in `_render_texture_pass` that prepends `u_` to keys. Remove it.
2. Update all `TexturePass` usage to include explicit `u_` prefixes in their uniform dicts.
3. Update all `prepare_uniforms` return dicts to consistently use `u_` prefixed keys.
4. Add a comment or docstring in `base_av_module.py` documenting the convention: "All uniform keys must be prefixed with `u_`. The renderer does not add prefixes." --> architect note: do not do this step. no need for the note. just remove the u_ appender and fixe everything.

**Test**: Verify all existing patches render identically before and after. Search all `.py` files for uniform dicts missing `u_` prefix.

**Acceptance**: Every uniform key in Python code starts with `u_`. No auto-prefix magic.

**Status (2026-03-11)**: ✅ Complete (`185fcc8`)
**Result**:

- Removed auto-prefixing from `_render_texture_pass`; `TexturePass.uniforms` keys now pass through verbatim.
- Updated internal module/shader pairs to explicit `u_` naming (`Composite`, `GridSwap`, `Media`, and additive blend helper shader path).
- Updated TexturePass-dependent module code (e.g. `BlueBackNGray`) to declare explicit `u_` keys.
- Added regression test proving pass uniforms are no longer auto-prefixed.
**Follow-up**:
- `ShadertoyModule` intentionally keeps native Shadertoy uniform names (`iResolution`, `iTime`, `iChannel`*) for compatibility; document this as an explicit exception in contributor docs.

---

## Priority D: General Improvements & Usability

---

### D1. Texture filter not forced every frame

**Seniority**: IC4 — small renderer fix
**Sprint**: Anytime (no deps, quick)
**File**: `core/renderer.py`
**Line**: ~164

**Problem**: `filter = (LINEAR, LINEAR)` is set on every input texture on every frame, overwriting module preferences and wasting a GPU property write per tick at 60fps.

**What to do**: Only set the filter when the texture is first created or when explicitly requested. Add a `filter` parameter to `TexturePass` and only set it if specified. Default to not overwriting.

**Acceptance**: Filter is set once at texture creation, not every frame.

---

### D2. Add `--profile` flag to render command

**Seniority**: IC4 — timer wrapping, straightforward
**Sprint**: Anytime after A2 (uses registry for per-module breakdown)
**Files**: `core/headless_renderer.py`, `cli.py`

**What to do**:

1. Add a `profile_frame(t: float) -> dict` method to `HeadlessRenderer` that wraps `render_frame(t)` with `time.perf_counter()` timing.
2. If the module graph is inspectable (after A2 registry), break down timing per module by timing each `render_texture` call.
3. Add `--profile` flag to `oblique render` that reports: total frame time in ms, estimated max FPS, and per-module breakdown if available.

**Acceptance**: `oblique render <patch> --t 1.0 --profile` outputs frame timing with per-module breakdown.

---

### D3. Deterministic rendering with `--seed` flag

**Seniority**: IC4 — uniform injection + convention doc
**Sprint**: Anytime (no deps)
**Files**: `core/headless_renderer.py`, `cli.py`

**Problem**: Some shaders use time-based noise or randomness. Rendering the same patch at the same `t` may produce different results if the shader uses non-deterministic inputs. An AI agent can't reproduce results it got on a previous render.

**What to do**:

1. Add a `--seed` flag to `oblique render`.
2. When set, inject a `u_seed` uniform into every render call with the seed value.
3. Shaders that use randomness should use `u_seed` instead of system time for their noise function inputs.
4. Document the convention: "For deterministic rendering, use `u_seed` in your shader. When `--seed` is passed, `u_time` is still available but `u_seed` provides a fixed random base."

**Acceptance**: `oblique render <patch> --t 1.0 --seed 42` produces identical output on every run.

---

### D4. A/B comparison rendering

**Seniority**: IC4 — builds on A3, clear input/output contract
**Sprint**: Anytime after A3 (depends on frame analysis)
**Files**: `core/headless_renderer.py`, `core/frame_analysis.py`, `cli.py`

**What to do**:

1. Add `HeadlessRenderer.compare(t: float, mutations: dict) -> dict` that:
  - Renders the original frame
  - Applies the mutations (param name → new value) to the patch
  - Renders the mutated frame
  - Returns `analyze_frame` for both, plus delta metrics and `hash_distance`
  - Restores original param values
2. Add `--compare '{"param": value}'` flag to `oblique render` that runs the comparison.

**Acceptance**: `oblique render <patch> --t 1.0 --compare '{"feedback_strength": 0.5}'` shows side-by-side stats and hash distance.

---

### D5. Module scaffolding command

**Seniority**: IC4 — string templating, but **have Sr. Architect review the generated module pattern** (this becomes the canonical "how to write a module" example)
**Sprint**: 4 (depends on A2, pairs with A7)
**Files**: `cli.py`, new file `templates/module_scaffold.py`

**What to do**:

1. Add `oblique new-module <category>/<name>` command that generates:
  - `modules/<category>/<name>.py` with: Params dataclass (with width/height or without if B1 is done), Uniforms TypedDict, Module class extending BaseAVModule, metadata, `@oblique_module` decorator, `prepare_uniforms` method
  - `modules/<category>/shaders/<name>.frag` with: `#version 330 core`, standard uniform declarations (`u_time`, `u_resolution`), a basic passthrough or noise shader body
2. Flags:
  - `--params "strength:float:0.5:0.0:1.0"` — param name, type, default, min, max
  - `--texture-inputs "input_texture"` — texture input params
  - `--description "..."` — module description

**Acceptance**: `oblique new-module effects/glow --params "intensity:float:1.0:0.0:5.0" --texture-inputs input_texture` generates a valid, runnable module + shader pair.

---

### D6. Parent → child uniform inheritance documentation or opt-in

**Seniority**: Sr. Architect — changes `TexturePass` dataclass contract and the implicit inheritance behavior. Requires understanding multi-pass module interactions across the whole codebase.
**Sprint**: 5 (pair with B1 refactor — both touch `base_av_module.py` deeply)
**File**: `modules/core/base_av_module.py`
**Method**: `_render_texture_pass` (around line 296)

**Problem**: Child `TexturePass` instances inherit ALL parent uniforms via `dict(inherited_uniforms)`. A child shader that declares `uniform float u_time;` silently receives the parent's time value. This is useful for some passes but a debugging nightmare for others.

**What to do**:

1. Add `inherit_parent_uniforms: bool = True` field to `TexturePass` dataclass.
2. When `False`, the child pass receives only its own explicitly declared uniforms plus `u_resolution`.
3. Default to `True` for backward compatibility.
4. Add a docstring on `TexturePass` explaining the inheritance behavior and when to disable it.

**Test**: Create a multi-pass module with `inherit_parent_uniforms=False` on one pass. Verify it does NOT receive parent uniforms.

**Acceptance**: `TexturePass` documentation explains inheritance. New field lets modules opt out.

**Status (2026-03-11)**: ✅ Complete (`8c60c38`)
**Result**:
- Added `inherit_parent_uniforms: bool = True` to `TexturePass` in `modules/core/base_av_module.py`.
- Updated `_render_texture_pass` to honor opt-out behavior: when disabled, pass uniforms start empty and only include explicit values plus `u_resolution`.
- Updated `TexturePass` docstring to document inheritance behavior and the opt-out switch.
- Added regression test `test_texture_pass_can_opt_out_of_parent_uniform_inheritance` in `tests/modules/test_base_av_module.py`.
**Follow-up**:
- Re-verify key multi-pass modules with intentional inheritance (e.g. shared timing uniforms) to ensure opt-out does not mask expected data flow.
- When B1 lands, revisit generated module templates to expose `inherit_parent_uniforms` in scaffolding examples where useful.
