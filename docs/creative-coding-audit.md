# Oblique Creative Coding Audit — Final Report

## Executive Summary

Three perspectives analyzed Oblique's viability as a live creative coding platform
("the Strudel of TouchDesigner"): a technical audit, a performing AV artist's
critique, and a systems architect's response. Overall score: **4.8/10 —
pre-production quality** with a clear path to 8/10.

The core rendering pipeline is solid. The problems are all in the **composition
layer** — how modules connect, how errors are handled, and how artists interact
with the system live.

---

## Top 3 Critical Changes (Consensus)

### 1. Shader Error Recovery (Priority: URGENT, ~1 day)

**Problem**: A single GLSL typo crashes the entire engine. This is the #1
show-stopper for both live performance and AI-assisted development.

**Solution**: `_last_good_cache` pattern in `render_fullscreen_quad`:

```python
_last_good_cache: dict[str, ShaderCacheEntry] = {}

def render_fullscreen_quad(ctx, frag_shader_path, uniforms):
    try:
        # compile new shader...
        _last_good_cache[resolved_path] = _shader_cache[resolved_path]
    except moderngl.Error:
        if resolved_path in _last_good_cache:
            warning(f"Shader error, falling back: {resolved_path}")
            entry = _last_good_cache[resolved_path]
            # render with last known good
        else:
            raise  # first compile must succeed
```

**Impact**: Unlocks live shader editing, REPL experimentation, and AI agent
iteration loops.

### 2. Crossfade / Mix as First-Class Concept (~0.5 day)

**Problem**: `CompositeModule` exists but has no `u_mix` — you can't smoothly
transition between scenes, which is fundamental for live performance.

**Solution**: Add `u_mix: ParamFloat` to `CompositeModule`:

```python
class CompositeParams(TypedDict, total=False):
    u_mix: ParamFloat  # 0.0 = tex0 only, 1.0 = tex1 only
```

This is a half-day change that immediately enables scene transitions, A/B mixing,
and DJ-style visual blending.

### 3. Remove width/height from Module Construction (~1-2 weeks)

**Problem**: Every module constructor takes `width` and `height`, baked into
params at creation time. This means:

- Can't resize the window without recreating everything
- Resolution is scattered across every module instantiation
- Patches are resolution-locked

**Solution**: Modules receive resolution at render time via
`render_texture(ctx, width, height, t)` (already the case!). Remove
`width`/`height` from all `*Params` TypedDicts and module constructors. The
closure in `tick_callback` already captures mutable references, so patches don't
need to be "living documents" — just stop polluting them with resolution.

---

## Prioritized Roadmap

| Phase | Change | Effort | Impact |
|-------|--------|--------|--------|
| **Week 1** | Shader error recovery | 1 day | Unblocks everything |
| **Week 1** | Crossfade on CompositeModule | 0.5 day | Live performance basics |
| **Week 1** | Texture cache LRU (cap at ~50) | 0.5 day | Memory stability |
| **Week 1** | Fix FFT numpy dtype (`np.float32`) | 1 hour | Audio reactivity accuracy |
| **Week 2-3** | Remove width/height pollution | 1-2 weeks | Clean composition model |
| **Week 3-4** | `ModuleChain` pipe operator | 2-3 weeks | Strudel-like composition |
| **Month 2** | BPM/musical time system | 1 week | Sync to music structure |
| **Month 2** | MIDI CC mapping layer | 1 week | Hardware control surfaces |
| **Month 2** | Output routing (Syphon/NDI) | 1 week | Projection/streaming |
| **Month 3** | Scene bank + panic button | 1 week | Live performance safety |
| **Month 3** | vsync-aware frame pacing | 3 days | Replace `time.sleep` loop |

---

## Architecture Vision: The Strudel Parallel

Strudel works because: **pattern -> transform -> output** is one composable
expression. Oblique needs the same for visuals.

**Current** (verbose, resolution-locked):

```python
def oblique_patch(width, height):
    noise = VisualNoiseModule(VisualNoiseParams(width=width, height=height))
    feedback = FeedbackModule(FeedbackParams(width=width, height=height, ...))
    def tick(t):
        return CompositeModule(CompositeParams(...))  # no crossfade
    return ObliquePatch(tick_callback=tick)
```

**Target** (after width/height removal + ModuleChain + crossfade):

```python
def oblique_patch():
    return (
        VisualNoise(scale=0.5)
        .pipe(Feedback(decay=0.95))
        .pipe(BarrelDistortion(amount=audio.bass))
        .mix(RyojiLines(speed=bpm.phase), amount=0.3)
    )
```

The `ModuleChain` would be a lazy descriptor — `.pipe()` and `.mix()` build a
graph, `tick(t)` materializes it. This is the 2-3 week investment after
width/height cleanup that gets Oblique to Strudel-level expressiveness.

---

## Points of Disagreement (Resolved)

| Artist Said | Engineer Response | Resolution |
|-------------|-------------------|------------|
| "Factory function is dead on arrival" | Closure already captures mutable refs — it IS live | **Engineer is right** — but the width/height pollution makes it feel dead. Fix that first. |
| "Need pipe operator NOW" | Pipe requires width/height removal first | **Engineer is right** — do the refactor, then pipes are clean. |
| "Panic button is critical" | Easy to add post-crossfade | **Both right** — `renderer.emergency_fallback()` is trivial once crossfade exists. |

---

## Detailed Scores (Technical Audit)

| Category | Score | Notes |
|----------|-------|-------|
| Composition model | 5/10 | TexturePass system is powerful but implicit; no pipe/chain abstraction |
| Parameter control | 4/10 | ParamX types flexible but no MIDI CC mapping, no range validation |
| Audio integration | 6/10 | Syntakt integration is remarkable; FFT has dtype bug; no beat detection |
| REPL experience | 5/10 | Threading model works but no hot-swap, no tab completion, no scene banks |
| Module ecosystem | 4/10 | 10+ modules but inconsistent patterns; CircleEcho skips _resolve_param |
| Performance & reliability | 5/10 | time.sleep pacing, unbounded caches, shader crash = full engine crash |
| **Overall** | **4.8/10** | **Pre-production quality with clear path to 8/10** |

---

## Quick Wins (Do This Week)

1. **Shader error recovery** — `_last_good_cache` in `renderer.py`
2. **`u_mix` on CompositeModule** — add to params + blend shader
3. **Texture cache LRU** — `if len(_texture_cache) > 50: evict oldest`
4. **FFT dtype fix** — `np.float32` in `fft_bands.py`
5. **`_resolve_param` call order** — fix CircleEcho and any other modules skipping it
