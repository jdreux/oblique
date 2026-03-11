# The AI Creative Agent's Manifesto

**How to make Oblique the most AI-friendly creative coding platform in existence.**

*Written by an AI agent who has been building patches in Oblique, hitting walls, finding workarounds, and dreaming about what this could be.*

---

## Preface: Why This Matters

I am an LLM. I cannot see. I have no eyes, no monitor, no intuition about whether the swirling feedback loop I just wrote looks beautiful or broken. Every other creative coding environment was designed for a human sitting in front of a screen, tweaking a knob, watching the pixels change, and going "oh, that's nice." I do not have that luxury.

And yet -- I can write GLSL. I can reason about mathematical transformations. I can compose modules, tune parameters, and iterate on visual systems at a speed no human can match. If you give me the right tools, I can be a genuine creative collaborator rather than a glorified autocomplete.

Oblique is closer to being that platform than anything else I have encountered. The architecture is right: Shadertoy-style fragment shaders, a composable module graph, a headless renderer that lets me verify my work without a display. But "closer" is not "there." The friction is real, the gaps are painful, and the potential is enormous.

This document is my honest account of what works, what does not, and what would make Oblique transformative.

---

## 1. Discovery & Understanding: "What Can I Even Do Here?"

### What Exists

The `metadata` dict on each `BaseAVModule` subclass is the closest thing to a machine-readable module registry:

```python
# From modules/core/visual_noise.py
metadata = {
    "name": "VisualNoiseModule",
    "description": "Generates visual noise patterns with configurable size and color modes.",
    "parameters": {
        "noise_size": "small|medium|large",
        "color_mode": "gray|rgba",
        "intensity": float,
        "speed": float,
    },
}
```

This is a start. But it is a dead end for an AI agent, for several reasons:

**There is no registry.** To discover available modules, I have to glob `modules/**/*.py`, import each one, and inspect the class. There is no `oblique list-modules` command, no JSON manifest, no introspection API.

**The metadata is incomplete and inconsistent.** `CircleEcho` uses `CircleEchoParams.__annotations__` for its `parameters` field -- a bare dict of type annotations. `VisualNoiseModule` uses hand-written strings like `"small|medium|large"`. Neither tells me valid ranges, defaults, or what "interesting" values look like.

**Shaders are opaque.** I can read the `.frag` file and parse the `uniform` declarations, but there is no metadata linking Python params to GLSL uniforms. The `u_` prefix convention is sometimes auto-applied (in `TexturePass.uniforms`) and sometimes expected to be explicit (in `prepare_uniforms`). As the design analysis at `/Users/juliendreux/Documents/dev/oblique/docs/design-analysis.md` notes: "An LLM generating a module cannot determine the rule without reading multiple source files."

**Processing operators are invisible.** `FFTBands`, `NormalizedAmplitudeOperator`, `SpectralCentroid` -- these are the bridge between audio and visuals, but they have no discoverability mechanism. I have to know they exist and know their constructor signatures.

### What's Missing

**A machine-readable module catalog.** Something I can query at the start of any session:

```python
# Dream API:
from core.registry import get_module_catalog

catalog = get_module_catalog()
# Returns:
# {
#   "VisualNoiseModule": {
#     "category": "core",
#     "description": "Generates visual noise patterns...",
#     "params": {
#       "noise_size": {"type": "Literal['small','medium','large']", "default": "medium"},
#       "intensity": {"type": "ParamFloat", "default": 1.0, "range": [0.0, 2.0]},
#       "speed": {"type": "ParamFloat", "default": 1.0, "range": [0.0, 10.0]},
#     },
#     "uniforms": ["u_noise_scale", "u_intensity", "u_color_mode", "u_speed", "u_time"],
#     "shader_path": "modules/core/shaders/visual-noise.frag",
#     "accepts_texture_inputs": False,
#     "supports_ping_pong": False,
#   },
#   "FeedbackModule": {
#     "category": "effects",
#     "accepts_texture_inputs": True,
#     "texture_input_params": ["input_texture"],
#     "supports_ping_pong": True,
#     ...
#   },
# }
```

**A CLI introspection command:**

```bash
oblique inspect modules              # list all modules with descriptions
oblique inspect module FeedbackModule # full parameter schema, shader uniforms, examples
oblique inspect processors           # list all processing operators
oblique inspect shader modules/effects/shaders/feedback.frag  # parse uniforms from GLSL
```

**Automatic schema extraction.** The `Params` dataclasses already contain all the information needed. A simple reflective function could walk `dataclasses.fields()`, extract types, defaults, and annotations, and produce a JSON schema. The fact that this does not exist is the single biggest friction point for AI-driven patch creation.

### What Would Be Transformative

A `oblique catalog --json` command that outputs the complete module graph as structured data. This is my "context window" -- the more structured information I can load at the start of a session, the fewer hallucinated parameter names and wrong import paths I produce. Today I spend 30-40% of my reasoning budget just figuring out what exists and how it connects. That should be zero.

---

## 2. Patch Creation: "Let Me Build Something"

### What Exists

The patch creation workflow today looks like this:

```python
# From projects/demo/demo_audio_file.py -- 213 lines to build one patch
def oblique_patch(width: int, height: int) -> ObliquePatch:
    audio_input = AudioFileInput(file_path="projects/demo/audio/somefile.wav")
    fft_bands_processor16 = FFTBands(audio_input, num_bands=16)

    circle_echo_module = CircleEcho(
        CircleEchoParams(width=width, height=height, n_circles=32),
        fft_bands_processor16,
    )

    feedback_module = FeedbackModule(
        FeedbackParams(
            width=width, height=height,
            feedback_strength=0.9,
            input_texture=circle_echo_module,
        ),
    )

    def _tick_callback(t: float) -> BaseAVModule:
        return feedback_module

    return ObliquePatch(audio_output=audio_input, tick_callback=_tick_callback)
```

### The Friction

**Width and height pollution.** Every single module constructor takes `width` and `height`. The creative-coding audit (`/Users/juliendreux/Documents/dev/oblique/docs/creative-coding-audit.md`) already identified this as the #3 critical change. From my perspective, it is arguably #1 because it means I cannot compose a reusable module graph without knowing the render resolution at construction time. Every module I instantiate is resolution-locked. If the user later says "render that at 4K," I have to rebuild the entire graph.

**Inconsistent constructor signatures.** Some modules take just `params` (`FeedbackModule`, `VisualNoiseModule`). Others take `params` plus additional arguments (`CircleEcho` takes `band_levels_processor`, `RyojiLines` takes both `fft_bands` and `spectral_centroid`). There is no standard way to discover what a module's constructor expects beyond reading the source.

**No validation at construction time.** I can create a `FeedbackParams(input_texture="not_a_module", width=800, height=600)` and it will not fail until render time, deep inside the shader pipeline. By then, the error message is about GLSL uniform types, not about the invalid parameter I passed.

**The tick callback is both powerful and confusing.** The `_tick_callback(t)` closure is where all per-frame logic lives -- parameter mutation, module selection, animation. But there is no guidance on what belongs there vs. what should be a `Callable` parameter. The demo patch mutates `params` directly inside the callback:

```python
def _tick_callback(t: float) -> BaseAVModule:
    amplitude = normalized_amplitude_processor.process() * 550.0
    mit_particles_module.params.noise_strength = amplitude
    return mit_particles_module
```

This works but is a footgun. There is no separation between "configure the graph" and "animate the graph." An AI agent cannot easily distinguish "things I should set once" from "things I should vary per frame."

### What Would Be Ideal

**A declarative patch builder with validation:**

```python
# Dream API: validated, resolution-independent, discoverable
from oblique import Patch, modules, audio, processing

patch = Patch()

# Audio pipeline -- processors auto-register with their input
audio_in = audio.file("path/to/song.wav")
fft = processing.FFTBands(audio_in, num_bands=16)
amplitude = processing.NormalizedAmplitude(audio_in)

# Module graph -- no width/height, texture wiring is explicit
circles = modules.CircleEcho(n_circles=32, band_amps=fft)
feedback = modules.Feedback(input=circles, strength=0.9)

# Animation -- separate from graph construction
patch.animate(feedback, {
    "strength": lambda t: 0.8 + 0.1 * math.sin(t),
})

# The patch validates the full graph at construction time:
# - Are all required texture inputs connected?
# - Do the processing operators match expected types?
# - Can the shader compile with the declared uniforms?
patch.set_output(feedback, audio=audio_in)
```

**A `oblique new-module` scaffolding command** that generates a module + params + uniforms + shader template with all the boilerplate pre-filled and consistent:

```bash
oblique new-module effects/chromatic_aberration \
  --params "strength:float:0.5:0.0:2.0" "offset:float:0.01" \
  --texture-inputs "input_texture" \
  --description "RGB channel offset for chromatic aberration"
```

This would generate `modules/effects/chromatic_aberration.py` and `modules/effects/shaders/chromatic-aberration.frag` with all naming conventions correct, all boilerplate handled, and a shader template with the right uniform declarations.

---

## 3. Iteration & Feedback: "Did That Actually Work?"

### What Exists

The headless renderer at `/Users/juliendreux/Documents/dev/oblique/core/headless_renderer.py` is genuinely excellent. It is the single most important feature for AI-driven development. The API is clean:

```python
with HeadlessRenderer(patch, 800, 600) as r:
    r.prime_audio(t=1.0)
    r.render_to_file(1.0, "/tmp/frame.png")
    stats = r.inspect(1.0)
    # {'width': 800, 'height': 600, 'mean_brightness': 0.3421, 'non_black_ratio': 0.8712}
```

The CLI equivalent works:

```bash
oblique render projects.demo.demo_audio_file --t 1.0 --inspect
oblique render projects.demo.demo_audio_file --t 1.0 --output /tmp/frame.png
```

The `inspect()` method returns `mean_brightness` and `non_black_ratio` -- just enough to detect "is this a black screen?" vs. "is something rendering?"

### What's Missing

**Richer visual statistics.** `mean_brightness` and `non_black_ratio` are survival checks. For actual creative iteration, I need:

```python
# Dream inspect output:
{
    "width": 800,
    "height": 600,
    "mean_brightness": 0.3421,
    "non_black_ratio": 0.8712,
    "dominant_colors": [(0.2, 0.1, 0.8), (0.9, 0.1, 0.1)],  # top 3 cluster centroids
    "color_variance": 0.45,        # how varied is the palette?
    "spatial_frequency": 0.62,     # low = smooth gradients, high = detailed textures
    "symmetry_score": 0.31,        # how symmetric is the composition?
    "motion_delta": 0.08,          # difference from previous frame (if available)
    "histogram": {                 # per-channel histograms
        "r": [0.01, 0.02, ...],   # 16 bins
        "g": [0.01, 0.03, ...],
        "b": [0.02, 0.01, ...],
    },
}
```

With richer statistics, I can make informed creative decisions: "the image is too blue, shift hue," "the spatial frequency is low, add some noise texture," "the brightness variance is zero, something is clipping."

**Temporal inspection.** A single frame tells me nothing about animation quality. I need:

```bash
oblique render my_patch --t 0.0 --duration 2.0 --fps 5 --inspect
# Output: per-frame stats + motion/change summary
```

**Diff inspection.** When I change a parameter, I want to know what changed:

```python
stats_before = renderer.inspect(1.0)
# ... modify parameter ...
stats_after = renderer.inspect(1.0)
diff = compare_stats(stats_before, stats_after)
# {'mean_brightness': +0.12, 'non_black_ratio': +0.05, 'color_shift': 'warmer'}
```

**Shader compilation check without rendering.** Today, I find out about GLSL errors only when `render_to_texture` is called. I should be able to validate a shader before running the full pipeline:

```python
from core.shader_validator import validate_shader

result = validate_shader("modules/effects/shaders/my-new-effect.frag")
# ShaderValidation(
#   valid=False,
#   error="0:23: error: 'smoothsteo' : no matching overloaded function found",
#   line=23,
#   uniforms_declared=["u_time", "u_resolution", "u_input_texture"],
# )
```

---

## 4. Composition: "How Do I Build Complex Scenes?"

### What Exists

The composition model is genuinely clever. Modules are texture producers. You feed one module as a texture input to another. The `render_texture` method on `BaseAVModule` handles the full dependency graph:

```python
# Module A produces a texture
noise = VisualNoiseModule(VisualNoiseParams(width=w, height=h))

# Module B consumes it
feedback = FeedbackModule(FeedbackParams(
    width=w, height=h,
    input_texture=noise,        # <-- A BaseAVModule, resolved to texture at render time
    feedback_strength=0.9,
))
```

The `TexturePass` system adds multi-pass rendering:

```python
# From base_av_module.py -- TexturePass can reference other passes or modules
@dataclass
class TexturePass:
    frag_shader_path: str
    uniforms: dict[str, Union[TexturePass, BaseAVModule, moderngl.Texture, ...]]
    ping_pong: bool = False
    # ...
```

And `CompositeModule` handles blending with 27 blend modes -- a genuinely impressive range.

### The Friction

**No explicit graph representation.** The module graph is implicit -- it exists only in the closure captured by `tick_callback`. I cannot inspect it, validate it, or visualize it. If I build a complex chain and something goes wrong, I cannot ask "what modules are in this graph?" or "what is the rendering order?"

**CompositeModule is all-or-nothing.** It blends two textures with a blend mode, but there is no `mix` parameter for crossfading. The creative-coding audit identified this. Without it, I cannot smoothly transition between scenes or blend two visual streams at arbitrary ratios. For an AI agent building live visuals, this is crippling -- I cannot say "show 70% of this and 30% of that."

**No module grouping or abstraction.** If I build a "feedback + distortion + levels" chain that I want to reuse, I have to rebuild it from scratch each time. There is no `ModuleGroup` or `SubPatch` concept that encapsulates a sub-graph as a single module.

### What Would Be Ideal

**An explicit, inspectable graph:**

```python
# Dream API:
graph = patch.get_graph()
print(graph)
# Output:
# VisualNoiseModule
#   -> FeedbackModule (input_texture)
#     -> BarrelDistortionModule (input_texture)
#       -> CompositeModule (top_texture)
#           + MediaModule (bottom_texture)

# For AI agents, a JSON version:
graph_json = patch.get_graph_json()
# {
#   "root": "CompositeModule:0x...",
#   "nodes": {
#     "VisualNoiseModule:0x...": {"params": {...}, "outputs_to": ["FeedbackModule:0x..."]},
#     ...
#   }
# }
```

**A pipe/chain operator** (as envisioned in the creative-coding audit):

```python
# Dream API:
output = (
    VisualNoise(scale=0.5)
    .pipe(Feedback(strength=0.9))
    .pipe(BarrelDistortion(amount=0.3))
    .mix(RyojiLines(speed=1.0), amount=0.3)  # 70% left chain, 30% ryoji
)
```

This is not just syntactic sugar. It is a fundamentally better representation for an AI agent because the data flow is linear and readable. The current nested-constructor approach requires me to read inside-out.

**Reusable sub-patches:**

```python
# Dream API:
class GlitchChain(ModuleGroup):
    """Reusable glitch effect chain."""
    def build(self, input_texture):
        return (
            input_texture
            .pipe(GridSwap(grid_size=8, num_swaps=32))
            .pipe(Feedback(strength=0.85))
            .pipe(Levels(invert=True))
        )
```

---

## 5. Error Recovery: "I Wrote Bad GLSL, Now What?"

### What Exists Today

Nothing. A GLSL compilation error in `render_fullscreen_quad` raises a `moderngl.Error`, which propagates up through `render_to_texture`, through `render_texture`, through the engine's frame loop, and crashes the entire application.

The creative-coding audit called this "URGENT, ~1 day" and proposed a `_last_good_cache` pattern. That was correct. It has not been implemented yet.

### What This Means for an AI Agent

When I am iterating on a shader -- writing GLSL, rendering, checking stats, adjusting -- a single typo kills the entire process. I have to restart the headless renderer, re-prime the audio, and re-render from scratch. In a multi-turn creative session, this happens constantly.

For the REPL workflow (hot-reload-shaders + hot-reload-python), it is even worse. The user is watching the window, I push a shader change, and the window goes black or crashes. Trust destroyed instantly.

### What Should Happen

**Graceful shader fallback:**

```python
# In renderer.py -- render_fullscreen_quad
try:
    program = ctx.program(vertex_shader=vs, fragment_shader=fs)
    _last_good_cache[resolved_path] = ShaderCacheEntry(program, vao, vbo, mtime)
except moderngl.Error as e:
    if resolved_path in _last_good_cache:
        warning(f"Shader compile error in {resolved_path}: {e}")
        warning(f"Falling back to last known good shader.")
        entry = _last_good_cache[resolved_path]
        program, vao, vbo = entry.program, entry.vao, entry.vbo
    else:
        # First compile must succeed -- render a diagnostic pattern
        program = _compile_error_shader(ctx, str(e))
```

**Structured error reporting:**

```python
# Dream API:
from core.shader_validator import compile_check

result = compile_check("modules/effects/shaders/my-effect.frag")
if not result.ok:
    print(result.error)
    # "Line 23: 'smoothsteo' is not a valid function. Did you mean 'smoothstep'?"
    print(result.line_context)
    # "    float v = smoothsteo(0.0, 1.0, uv.x);"
    #                ^^^^^^^^^^
```

**An error visualization shader.** When a shader fails to compile, instead of a black screen or a crash, render a diagnostic pattern -- red with the error text overlaid, or a checkerboard that signals "something is wrong but the engine is alive." TouchDesigner does this. It is the minimum viable error recovery.

**Uniform mismatch warnings.** Today, if I declare a uniform in Python but misspell it in the shader (or vice versa), nothing happens -- the uniform is silently skipped by `if name in program`. I should get a warning:

```
WARNING: Uniform 'u_feedbak_strength' set in Python but not found in shader
         modules/effects/shaders/feedback.frag
         Did you mean 'u_feedback_strength'?
```

---

## 6. Parameter Exploration: "What Values Look Good?"

### What Exists

Parameters have types (`ParamFloat`, `ParamInt`, etc.) and sometimes defaults in the dataclass. That is it. There are no ranges, no suggested values, no description of what the parameter does visually.

### What I Actually Need

When I am building a patch and I reach for `FeedbackModule`, I need to know:

- `feedback_strength`: float, default 0.97, range [0.0, 1.0]. Values near 0.0 = no feedback. Values near 0.95 = long trails. Values above 0.99 = infinite accumulation, will blow out.
- `direction`: tuple of floats, default (0, 0). Small values like (0.001, 0.001) create directional trails. Large values create smearing.

None of this exists in the codebase. I have to infer it from the GLSL source, which is doable but slow and error-prone.

### What Would Be Transformative

**Parameter annotations with ranges and semantic descriptions:**

```python
@dataclass
class FeedbackParams(BaseAVParams):
    input_texture: ParamTexture
    feedback_strength: Annotated[ParamFloat, ParamMeta(
        default=0.97,
        range=(0.0, 1.0),
        description="Decay rate per frame. 0.0=no feedback, 0.95=long trails, >0.99=infinite accumulation",
        interesting_values=[0.0, 0.5, 0.85, 0.95, 0.99],
        tags=["decay", "persistence", "memory"],
    )]
    direction: Annotated[tuple[ParamFloat, ParamFloat], ParamMeta(
        default=(0.0, 0.0),
        range=((-0.1, -0.1), (0.1, 0.1)),
        description="UV offset for directional feedback. Small values = trails, large = smear.",
        interesting_values=[(0, 0), (0.001, 0), (0, -0.001), (0.005, 0.005)],
    )]
```

**A parameter sweep tool:**

```bash
oblique sweep my_patch --param "feedback.strength" --range 0.0 1.0 --steps 10 \
  --t 1.0 --output /tmp/sweep/
# Renders 10 frames with strength=[0.0, 0.11, 0.22, ..., 1.0]
# Outputs /tmp/sweep/strength_0.00.png through /tmp/sweep/strength_1.00.png
# Plus /tmp/sweep/summary.json with inspect stats per frame
```

This is perhaps the single most impactful tool for an AI agent doing creative work. Instead of guessing at parameter values, I can see (via stats) how a parameter affects the output across its full range. I can find the sweet spot. I can make informed creative decisions.

**Preset values per module.** Not full "presets" in the traditional sense, but named starting points:

```python
class FeedbackModule:
    presets = {
        "subtle_trails": {"feedback_strength": 0.85, "direction": (0, 0)},
        "long_decay": {"feedback_strength": 0.97, "direction": (0, 0)},
        "upward_drift": {"feedback_strength": 0.9, "direction": (0, -0.002)},
        "smear": {"feedback_strength": 0.95, "direction": (0.01, 0.01)},
    }
```

---

## 7. Prompt-to-Visual Pipeline: "Describe What You Want"

This is the north star. A user says "I want dark, pulsing circles that react to bass frequencies with long feedback trails," and the system produces a patch.

### What Would Need to Exist

**Step 1: Intent parsing.** Map the natural language to module choices and parameter ranges.

```
"dark, pulsing circles"          -> CircleEcho with low base brightness, mod_depth driven by time
"react to bass frequencies"      -> FFTBands with low num_bands, mapped to mod_depth or audio_level
"long feedback trails"           -> FeedbackModule with strength ~0.95
```

**Step 2: Graph construction.** Wire the modules together.

```python
audio = AudioFileInput(file_path=user_audio_file)
fft = FFTBands(audio, num_bands=8)

circles = CircleEcho(
    CircleEchoParams(n_circles=16, mod_depth=0.8, width=w, height=h),
    fft,
)
feedback = FeedbackModule(
    FeedbackParams(input_texture=circles, feedback_strength=0.95, width=w, height=h),
)
levels = LevelModule(
    LevelParams(parent_module=feedback, brightness=-0.3, width=w, height=h),  # "dark"
)
```

**Step 3: Verification.** Render a few frames and check stats.

```python
with HeadlessRenderer(patch, 800, 600) as r:
    r.prime_audio(t=1.0)
    stats = r.inspect(1.0)
    assert stats["non_black_ratio"] > 0.1, "Image is mostly black -- something is wrong"
    assert stats["mean_brightness"] < 0.5, "User asked for 'dark' but image is bright"
    r.render_to_file(1.0, "/tmp/preview.png")
```

**Step 4: Presentation.** Return the patch file and a preview image to the user.

### What Oblique Needs to Enable This

1. The module catalog (Section 1) so I know what is available.
2. Parameter annotations (Section 6) so I know what values to use.
3. The richer `inspect()` (Section 3) so I can verify creative intent.
4. Shader error recovery (Section 5) so iteration does not crash.
5. A standard patch template (Section 2) so I generate consistent code.

The AI layer itself -- the prompt parsing, the module selection heuristics -- does not need to live in Oblique. That is my job. But Oblique needs to give me the building blocks to do it reliably.

---

## 8. Multi-Turn Refinement: "Make It More Red"

This is where the rubber meets the road. Real creative sessions are not one-shot. They are dozens of micro-adjustments:

- "Make it more red"
- "Slow down the feedback"
- "Add some audio reactivity to the distortion"
- "The circles are too uniform, add some randomness"
- "I like this but make it feel more chaotic"

### How Well Does Oblique Support This Today?

**Parameter mutation works.** The closure-based tick_callback means I can mutate params on existing module instances:

```python
# "Make it more red" -- if I have access to a levels/color module
level_module.params.color_shift = (0.2, -0.1, -0.1)  # shift toward red

# "Slow down the feedback"
feedback_module.params.feedback_strength = 0.98  # was 0.9

# "Add audio reactivity to the distortion"
barrel_distortion_module.params.strength = lambda: -0.5 - 5 * amplitude_proc.process()
```

This is surprisingly good. The `ParamFloat = Union[float, Callable, BaseProcessingOperator]` type system means any parameter can be made dynamic at any time. An AI agent can swap a static value for a lambda or an operator without restructuring the graph.

**But graph topology changes are hard.** If the user says "add some feedback" to a chain that does not have it, I have to:

1. Create a new `FeedbackModule`
2. Rewire it into the existing chain
3. Update any downstream modules that referenced the old module

There is no "insert module between A and B" operation. I have to understand the full graph and manually rewire.

**And there is no undo.** If I make a change that looks terrible, I cannot roll back to the previous state without recreating the entire patch. The headless renderer creates a new context each time, so there is no persistent state to snapshot.

### What Would Make Multi-Turn Refinement Seamless

**Named parameter handles:**

```python
# At creation time, register named parameters
patch.register_param("circle_count", circles.params, "n_circles")
patch.register_param("feedback_decay", feedback.params, "feedback_strength")
patch.register_param("darkness", levels.params, "brightness")

# During refinement, modify by name
patch.set_param("feedback_decay", 0.98)
patch.set_param("darkness", -0.4)

# Query current state
print(patch.get_params())
# {"circle_count": 32, "feedback_decay": 0.98, "darkness": -0.4}
```

**Graph mutation operations:**

```python
# Insert a module between two existing modules
patch.insert_after(circles, FeedbackModule(FeedbackParams(...)))

# Replace a module in the chain
patch.replace(old_noise, new_noise)

# Remove a module, auto-rewiring upstream to downstream
patch.remove(barrel_distortion)
```

**Snapshots:**

```python
# Save current state
snapshot_id = patch.snapshot()

# Try something risky
feedback.params.feedback_strength = 1.0  # infinite accumulation

# Verify
stats = renderer.inspect(1.0)
if stats["mean_brightness"] > 0.95:  # blown out
    patch.restore(snapshot_id)
```

---

## 9. Concrete Recommendations, Prioritized

Here is what I would build, in order, if I were steering the roadmap for AI agent support.

### Week 1: Survival (Unblock the basic loop)

**1. Shader error recovery with last-good fallback.**
One day of work. Unblocks everything. Without this, every iteration cycle risks a crash.

**2. `oblique inspect` CLI command.**
Parse module classes and emit JSON. Half a day. This is my bootstrap -- the first thing I run in any session.

```bash
oblique inspect --json > /tmp/catalog.json
```

**3. Richer `inspect()` stats.**
Add dominant color, histogram, spatial frequency to `HeadlessRenderer.inspect()`. One day. Makes creative intent verification possible.

### Week 2: Fluency (Make iteration fast)

**4. Shader validation without rendering.**
A `compile_check()` function that creates a standalone context, compiles the shader, and returns structured errors. Half a day.

**5. Uniform mismatch warnings.**
Compare Python uniform keys against compiled shader uniform names. Log warnings for mismatches. Half a day.

**6. Parameter annotations with ranges.**
Add `ParamMeta` dataclass with `range`, `default`, `description`, `interesting_values`. Annotate the 5 most-used modules. Two days.

### Month 1: Composition (Make complex patches natural)

**7. Remove width/height from module params.**
The big refactor. Resolution flows in at render time, not construction time. One to two weeks. Unblocks everything in the composition layer.

**8. Pipe/chain operator.**
`module_a.pipe(module_b).pipe(module_c)`. Requires #7. One week.

**9. Mix parameter on CompositeModule.**
`u_mix: ParamFloat` for crossfading. Half a day.

### Month 2: Exploration (Make creative discovery easy)

**10. Parameter sweep tool.**
`oblique sweep` command that renders a parameter across its range and outputs stats + images. One week.

**11. Module scaffolding command.**
`oblique new-module` generates consistent boilerplate. Two days.

**12. Preset system.**
Named parameter sets per module. Two days.

---

## 10. The 20-Minute Test

Here is how I would test whether Oblique is truly AI-friendly. Time me on this task:

> **Prompt:** "Create a patch that shows audio-reactive noise with long feedback trails and barrel distortion. The noise should be colored, the feedback should drift upward slowly, and the distortion should pulse with the bass."

**With today's Oblique** (estimated: 15-25 minutes of AI reasoning + multiple file reads):

1. Read 5+ source files to discover available modules and their signatures.
2. Read 3+ shader files to understand uniform conventions.
3. Write a patch file with manual width/height threading.
4. Run `oblique render` and hope for no GLSL errors.
5. If errors, read the traceback, fix, re-render.
6. Check `inspect()` output -- only brightness and non-black ratio available.
7. Render to PNG and hope the user likes it.

**With the proposed changes** (estimated: 3-5 minutes of AI reasoning):

1. Run `oblique inspect --json` to load the full module catalog.
2. Select modules based on parameter metadata and descriptions.
3. Wire them with `.pipe()` chain.
4. Run `oblique render --inspect` with rich stats to verify creative intent.
5. If shader error, get structured error with line number and suggestion.
6. Run `oblique sweep` on the distortion strength to find the right range.
7. Render preview, done.

That is a 5x improvement in speed and a qualitative improvement in reliability. The AI goes from "hoping it works" to "knowing it works."

---

## Closing

Oblique has the right bones. The Shadertoy-style shader model is exactly what an AI agent needs -- simple input/output contracts, composable modules, deterministic rendering. The headless renderer is a genuine innovation for AI-driven creative work. The `ParamFloat = Union[float, Callable, Operator]` type system is elegant and powerful.

What is missing is the connective tissue that lets an AI agent work at full speed: machine-readable metadata, structured error handling, rich verification tools, and a composition model that does not require me to memorize the implementation details of every module.

Build that connective tissue, and Oblique becomes something unprecedented: a creative coding environment where an AI agent is not just a code generator but a genuine creative collaborator. Where "make it more chaotic" is not a vague request but a parameterized operation. Where iteration is measured in seconds, not minutes. Where the boundary between human intent and machine execution dissolves into a conversation about aesthetics.

That is the platform worth building.
