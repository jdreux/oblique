# Making Oblique AI-Native: Final Architecture Report

*Synthesized from dual perspectives: an AI creative agent's manifesto and a systems architect's response.*

---

## Executive Summary

Oblique's rendering pipeline is solid. The gap to becoming an AI-native creative coding platform is not in the GPU layer — it's in **discoverability, feedback, and safety**. An AI agent working with Oblique today spends 60% of its time on discovery (reading 23 files to find what's available), gets nearly zero feedback on its output (2 metrics from `inspect()`), and risks crashing the engine with a single GLSL typo.

Three changes unlock everything: a **module registry** (70 lines), **shader error recovery** (15 lines), and **rich frame analysis** (~100 lines of numpy). Together, these transform Oblique from a human-authored tool into an AI-native creation platform.

---

## The Core Problem

An AI agent creating a patch today must:

1. Glob `modules/**/*.py` and read 23 files to discover what modules exist
2. Parse inconsistent `metadata` dicts (three different conventions across modules)
3. Guess parameter ranges (no min/max annotations anywhere)
4. Thread `width, height` through every module constructor (~30% boilerplate)
5. Wire audio inputs → FFT processors → modules → effects → composites manually
6. Render and inspect with only `mean_brightness` and `non_black_ratio` as feedback
7. Hope the GLSL compiles — a single typo kills the engine

The gap from "make something that pulses to the beat" to a working patch is **~50 lines of code and 10 design decisions**. It should be 5 lines.

---

## Architecture: Seven Layers

### Layer 1: Module Registry (Foundation — Do First)

Everything depends on this. A decorator-based registry with auto-discovery:

```python
@oblique_module(
    category="audio_reactive",
    description="Concentric circles modulated by FFT band amplitudes",
    tags=["geometric", "concentric", "audio-reactive", "rhythmic", "minimal"],
    cost_hint="low",
)
class CircleEcho(BaseAVModule): ...
```

**ParamSpec** with range annotations:

```python
@dataclass
class ParamSpec:
    name: str
    type: str           # "float", "int", "bool", "texture", "enum"
    default: Any
    min: float | None
    max: float | None
    description: str
    semantic: str        # "brightness", "speed", "frequency"
```

**CLI surface:**

```bash
oblique list-modules --json          # All modules with structured metadata
oblique list-modules --tag organic   # Filter by tag
oblique describe FeedbackModule      # Full param specs, dependencies, cost
oblique search "pulsing geometric"   # Intent-based search over tags + descriptions
```

**Tag taxonomy** for semantic search:

```
Visual:   geometric | organic | glitch | minimal | dense | noisy | clean
Motion:   static | pulsing | flowing | chaotic | rhythmic | evolving
Audio:    audio-reactive | beat-sync | frequency-split | amplitude
Color:    monochrome | colorful | dark | bright | neon | muted
Effect:   distortion | feedback | blur | composite | transform | particle
```

**Effort**: ~2 days. **Impact**: Transforms every AI interaction.

### Layer 2: Shader Error Recovery (Urgent — Do First)

The `_last_good_cache` pattern in `renderer.py`:

```python
_last_good_cache: dict[str, ShaderCacheEntry] = {}

def render_fullscreen_quad(ctx, frag_shader_path, uniforms):
    try:
        program = ctx.program(vertex_shader=vert, fragment_shader=frag)
        _last_good_cache[resolved_path] = entry
    except moderngl.Error as e:
        if resolved_path in _last_good_cache:
            warning(f"Shader error, falling back: {e}")
            entry = _last_good_cache[resolved_path]
        else:
            raise  # first compile must succeed
```

Plus **uniform contract verification** in debug mode:

```python
if debug:
    shader_uniforms = set(program)
    provided = set(uniforms.keys())
    missing = shader_uniforms - provided - {"in_vert", "in_uv"}
    extra = provided - shader_uniforms
    if missing: warning(f"Shader expects but not provided: {missing}")
    if extra: warning(f"Provided but shader ignores: {extra}")
```

**Effort**: 1 day. **Impact**: Unlocks fearless experimentation.

### Layer 3: Rich Frame Analysis

Expand `inspect()` from 2 metrics to 16+, all pure numpy:

```python
def analyze_frame(arr: np.ndarray) -> dict:
    return {
        # Brightness
        "mean_brightness": ...,
        "brightness_std": ...,
        "non_black_ratio": ...,
        "clipped_ratio": ...,       # overexposed pixels

        # Color
        "mean_color_rgb": [...],
        "color_variance": ...,
        "mean_saturation": ...,
        "dominant_hue": "blue",     # human-readable from 12-bin histogram

        # Structure
        "edge_density": ...,         # Sobel gradient magnitude
        "spatial_balance": ...,      # quadrant brightness uniformity
        "center_brightness": ...,
        "edge_brightness": ...,

        # Derived signals
        "is_blank": bool,
        "is_saturated": bool,
        "is_dark": bool,
        "has_color": bool,
    }
```

**Temporal analysis** for sequences:

```python
def analyze_temporal(frames: list[np.ndarray]) -> dict:
    return {
        "mean_motion": ...,       # average frame-to-frame change
        "motion_variance": ...,   # stability of motion
        "is_static": bool,
        "is_chaotic": bool,
        "motion_profile": [...],  # per-frame motion values
    }
```

**Perceptual hashing** for frame comparison (Hamming distance < 10 = visually similar):

```python
def perceptual_hash(arr: np.ndarray) -> str: ...
def hash_distance(h1: str, h2: str) -> int: ...
```

**Effort**: 3 days. **Impact**: AI agents can finally "see" their output.

### Layer 4: Validation Layer (Pre-Flight Checks)

Three-phase validation before GPU execution:

1. **Static validation** (instant): module exists, params type-check, ranges respected, graph is acyclic
2. **Shader pre-validation** (fast): `glslangValidator` offline lint for GLSL syntax
3. **Runtime validation** (debug mode): uniform contract verification, missing texture detection

```bash
oblique validate projects.demo.demo_audio_file
# [OK] Static: 4 nodes, 3 connections, all modules found
# [OK] Shaders: 4 fragments compiled
# [WARN] FeedbackModule.feedback_strength has no range annotation
```

**Effort**: 3 days. **Impact**: AI never crashes the engine.

### Layer 5: Templates & Scaffolds

Opinionated starting points that encode the 10 design decisions an AI currently makes manually:

```bash
oblique new audio-reactive --audio track.wav --module RyojiLines --feedback
oblique new feedback-loop --module VisualNoise --distortion barrel
oblique new layered --modules CircleEcho,RyojiLines --blend screen
oblique new blank-canvas
```

Template library:

```
templates/
    audio_reactive.py     # Source + FFT → Module → optional Feedback
    feedback_loop.py      # Module → Feedback → Distortion (self-feeding)
    layered_composite.py  # Two sources → Composite with blend mode
    glitch_stack.py       # Source → GridSwap → Distortion → Level
    blank_canvas.py       # Minimal: one module, no audio
```

**Effort**: 2 days. **Impact**: Reduces 50-line gap to 5-line gap.

### Layer 6: Patch IR (Intermediate Representation)

A machine-readable JSON format for patches that LLMs can generate and validate:

```json
{
  "audio_source": {"type": "AudioFileInput", "file_path": "track.wav"},
  "nodes": [
    {"id": "visual", "module": "CircleEcho", "params": {"n_circles": 32}},
    {"id": "feedback", "module": "FeedbackModule",
     "params": {"feedback_strength": 0.9},
     "inputs": {"input_texture": "visual"}}
  ],
  "output": "feedback"
}
```

**Diff-friendly mutations** as first-class operations:

```json
[
  {"type": "set_param", "node": "feedback", "param": "feedback_strength", "value": 0.7},
  {"type": "insert_between", "source": "visual", "target": "feedback",
   "new_node": {"id": "blur", "module": "BlurModule", "params": {"blur_amount": 5.0}}}
]
```

**Architect's caveat**: Start with IR as a **read** format only (`oblique inspect-patch --json`). Build the compile direction (JSON → ObliquePatch) only after confirming AI agents benefit from it. LLMs are already good at writing Python — the IR must prove its value over raw Python generation.

**Effort**: 1 week (read direction), 2 weeks (compile direction). **Impact**: High if validated.

### Layer 7: Cost Model & Constraints

**Cost model**: Empirical render-time table per module, adjusted for resolution:

```bash
oblique render my_patch --t 1.0 --profile
# Frame time: 12.3ms (target: 16.6ms for 60fps)
# Breakdown:
#   ryoji_lines:    3.2ms (26%)
#   feedback:       1.8ms (15%)
#   barrel:         1.5ms (12%)
# Verdict: OK for 60fps, 4.3ms headroom
```

**Constraint system**: Declarative intent that the system validates during iteration:

```python
constraints = ConstraintSet(
    frame=[
        FrameConstraint("mean_brightness", "lt", 0.3, "keep it dark"),
        FrameConstraint("has_color", "eq", True, "should have color"),
    ],
    temporal=[
        FrameConstraint("mean_motion", "gt", 0.01, "must be responsive"),
    ],
    performance=[
        PerformanceConstraint("render_time_ms", "lt", 16.6),  # 60fps
    ],
)
```

**Architect's caveat**: Keep constraints in a separate library, not in core. Rich `analyze_frame()` metrics let the AI implement its own constraint logic.

---

## Points of Agreement

| Topic | AI Agent | Architect | Verdict |
|-------|----------|-----------|---------|
| Module registry is the keystone | "Reduces discovery from 23 files to one call" | "70 lines, everything depends on it" | **Do first** |
| Shader crash is #1 blocker | "Russian roulette with every GLSL edit" | "15 lines in renderer.py" | **Do first** |
| 2 metrics is not enough | "I am nearly blind" | "16 metrics, all pure numpy" | **Do in week 2** |
| Templates reduce friction | "50 lines should be 5" | "Encode the 10 design decisions" | **Do in week 3** |
| `_resolve_param` bug is real | "Operators can't be used as param values" | "1-line swap fixes it" | **Fix immediately** |

## Points of Disagreement

| Topic | AI Agent Says | Architect Says | Resolution |
|-------|---------------|----------------|------------|
| width/height removal priority | Top 5, do soon | Right goal, wrong timing — wait for registry | **Architect wins**: registry makes the refactor mechanical |
| Patch IR | Essential for AI workflow | Start read-only, validate before building compiler | **Architect wins**: don't build a DSL nobody uses |
| 15 vs 16 metrics | Wants SSIM, optical flow | Pure numpy only, no scipy/opencv deps | **Architect wins**: perceptual hash gets 80% at 1% complexity |
| Constraint system | Part of core | Separate library, let AI implement its own | **Architect wins**: rich metrics are the real value |

## What the Architect Added

Three ideas the AI agent didn't mention:

1. **Deterministic rendering**: `--seed` flag for reproducible GPU randomness. If the AI can't reproduce a result, it can't learn from it.
2. **A/B rendering**: `oblique render --mutation '{"feedback_strength": 0.5}' --compare-to original`. Try a change, see the diff, keep or discard.
3. **Module hot-instantiation**: `patch.replace_module(old, new)` for live graph modification without recreating the patch.

---

## Implementation Roadmap

| Week | What | Lines | Impact |
|------|------|-------|--------|
| **1** | Shader error recovery (`renderer.py`) | ~15 | Unblocks all AI iteration |
| **1** | Fix `_resolve_param` ordering (`base_av_module.py`) | ~2 | Bug fix, operators work as params |
| **1** | Module registry (decorator + auto-discovery + CLI) | ~150 | Foundation for everything |
| **2** | Rich `analyze_frame()` in headless renderer | ~100 | AI agents can see |
| **2** | Param annotations (min/max/description) on all modules | ~200 | AI agents know ranges |
| **3** | `analyze_temporal()` + perceptual hashing | ~60 | AI agents can compare |
| **3** | Templates (4 common patterns + CLI) | ~200 | 50-line gap → 5-line gap |
| **4** | Shader pre-validation (`glslangValidator`) | ~40 | Catch errors before GPU |
| **4** | Uniform contract verification (debug mode) | ~20 | Silent failures become visible |
| **5** | Cost model (empirical table + `--profile`) | ~80 | AI understands tradeoffs |
| **5** | Patch IR read direction (`--inspect-patch --json`) | ~150 | Machine-readable patch graphs |
| **6** | A/B rendering + deterministic `--seed` | ~60 | Controlled experimentation |
| **7+** | Patch IR compile direction (JSON → ObliquePatch) | ~300 | Only if read direction proves value |
| **Later** | Remove width/height from params | ~500 | Large refactor, depends on registry |

**Weeks 1-2 deliver immediate AI agent productivity. Weeks 3-4 make the iteration loop tight. Everything after that is validated incrementally.**

---

## The Vision

An AI agent working with Oblique in 4 weeks:

```
Agent: oblique list-modules --tag "audio-reactive,geometric" --json
→ CircleEcho, RyojiLines, PauricSquares (with full param specs)

Agent: oblique new audio-reactive --module CircleEcho --audio track.wav --format json
→ PatchGraph JSON with sensible defaults

Agent: oblique validate /tmp/patch.json
→ [OK] All checks passed

Agent: oblique render /tmp/patch.json --t 1.0 --inspect
→ { "mean_brightness": 0.34, "dominant_hue": "blue", "edge_density": 0.23,
     "has_color": true, "is_dark": false, "spatial_balance": 0.87 }

Agent: oblique render /tmp/patch.json --t 1.0 --mutation '{"n_circles": 64}' --compare-to original
→ { "brightness_delta": +0.12, "hash_distance": 18, "motion_delta": +0.03 }

Agent: oblique render /tmp/patch.json --duration 2 --fps 10 --inspect
→ { "mean_motion": 0.04, "is_static": false, "is_chaotic": false,
     "beat_correlation": 0.72 }
```

**Discovery → Generate → Validate → Render → Inspect → Mutate → Compare → Converge.**

Each step is one CLI call. Each returns structured JSON. No file reading, no guessing, no crashes. The AI agent spends 100% of its time on creative decisions and 0% on plumbing.

That's the Strudel of TouchDesigner — turbocharged for AI.
