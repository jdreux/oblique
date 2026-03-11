# Oblique Design Analysis

Findings from a full codebase audit. Organized by priority.

---

## Critical Bugs

### 1. Wrong types in `*Uniforms` TypedDicts
`FeedbackModule`, `TransformModule`, and `CompositeModule` annotate texture uniforms as
`BaseAVModule` or `ParamTexture` — raw Python objects — but the renderer expects
`moderngl.Texture`. This works today only because `TexturePass` routing resolves them
incidentally. The type annotations are actively misleading for anyone writing new modules.

```python
# composite_module.py — wrong:
class CompositeUniforms(Uniforms, total=True):
    top_tex: BaseAVModule   # should be moderngl.Texture
    bottom_tex: BaseAVModule
```

### 2. `_resolve_param()` checks `Callable` before `BaseProcessingOperator`
`BaseProcessingOperator` is callable, so the `isinstance(param, Callable)` branch fires
first, calling `param()` instead of `param.process()`. The operator branch is effectively
dead code.

```python
# base_av_module.py — wrong order:
if isinstance(param, Callable):          # catches operators too
    return param()
elif isinstance(param, BaseProcessingOperator):  # never reached
    return param.process()
```

### 3. `CircleEcho.prepare_uniforms` skips `_resolve_param()`
`n_circles`, `mod_depth`, `audio_level` are typed `ParamInt`/`ParamFloat` but passed raw
to the shader dict. Lambdas or operators are sent directly to the GLSL uniform.

---

## Memory / Performance

### 4. Ping-pong history grows unbounded
`_texture_history` keys encode `frame_index % 2` but old entries (different resolution or
tag) are never evicted. After hours of running, accumulates dead GPU allocations.
Fix: keep only 2 entries per `(pass_tag, width, height)` triple.

### 5. Texture cache has no eviction
`_texture_cache` in `renderer.py` grows forever. Each unique `cache_tag` creates a
permanent GPU allocation. Should cap at N entries or track by stable key.

### 6. Filesystem `stat` on every render frame
`os.path.getmtime()` + `resolve_asset_path()` is called per-frame unconditionally.
At 60 FPS = 3 600 syscalls/second even when hot reload is disabled. Gate behind
`if _hot_reload_shaders_enabled`.

### 7. Texture filter forced `LINEAR` on every frame
`renderer.py:164` sets `filter = (LINEAR, LINEAR)` on every input texture every frame,
overwriting whatever the module requested and wasting a GPU property write per tick.

---

## Shader Composition — Implicit Contracts

These are the biggest issues for AI code generation; there is no single canonical source
that specifies the full contract between Python, uniforms, and GLSL.

### 8. `u_` prefix convention is implicit and inconsistent
`_render_texture_pass` auto-adds `u_` to `TexturePass.uniforms` keys, but
`prepare_uniforms()` keys pass through raw. `CompositeModule` mixes `"top_tex"` (no prefix)
with `"u_op"` (with prefix) in the same dict. No linter enforces the convention.
**An LLM generating a module cannot determine the rule without reading multiple source files.**

### 9. Parent uniforms silently cascade into child `TexturePass`
`_render_texture_pass` seeds each child with `dict(inherited_uniforms)`, meaning a child
pass inherits all uniforms from the parent — including `u_resolution`, textures, and
primitives. A child can shadow or be polluted by parent values in ways that are hard to debug.

### 10. No contract between `Params`, `Uniforms`, and the GLSL shader
The three-way relationship — Python params → `prepare_uniforms()` dict → GLSL uniform names
— is never validated. The renderer silently skips any key not present in the compiled
shader (`if name in program`). An LLM must guess all three simultaneously and get them
exactly right or get silent failures.

### 11. `TexturePass` width/height resolution uses falsy check
```python
pass_width = pass_obj.width or parent_width  # width=0 falls through silently
# should be:
pass_width = pass_obj.width if pass_obj.width is not None else parent_width
```

---

## Module Inconsistencies

### 12. No canonical module pattern
Side-by-side comparison of four modules reveals:

| Aspect | CircleEcho | RyojiLines | Feedback | MediaModule |
|--------|-----------|------------|----------|-------------|
| Resolution | raw `params.width` | `_resolve_param()` | `_resolve_resolution()` | pre-computed |
| Array uniforms | `Tuple[float, ...]` | `List[float]` | — | — |
| Texture inputs | in `prepare_uniforms` | — | raw `ParamTexture` | overrides `render_texture` |
| `u_time` | ✗ | ✓ | ✓ | ✓ |
| Return style | inline dict | built dict | built dict | `return {...}` |

There is no single canonical template an LLM can follow reliably.

---

## Recommendations (Prioritized)

**Tier 1 — Correctness:**
1. Fix `_resolve_param()`: check `BaseProcessingOperator` before `Callable`
2. Fix `*Uniforms` TypedDicts to use `moderngl.Texture`
3. Fix `pass_obj.width or parent_width` → `is not None`
4. Ensure `CircleEcho` calls `_resolve_param()` on all `ParamX` fields

**Tier 2 — Memory:**
5. Cap `_texture_history` to 2 entries per `(pass_tag, w, h)` — evict on write
6. Add LRU eviction to `_texture_cache` (e.g. 64-entry max)
7. Gate `getmtime` behind `if _hot_reload_shaders_enabled`

**Tier 3 — AI Code Generation:**
8. Define one canonical `example_module.py` that shows the exact pattern end-to-end
9. Standardise the `u_` convention: require explicit prefix everywhere (drop auto-add)
10. Add a `validate_uniforms()` debug-mode check that compares Python keys against the
    compiled shader's declared uniforms — surface mismatches at startup not at render time
11. Document parent → child uniform inheritance explicitly in `TexturePass` docstring,
    or make it opt-in
