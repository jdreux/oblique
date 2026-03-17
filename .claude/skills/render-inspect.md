---
description: "Render a patch or module headless and return frame metrics + alpha analysis. Usage: /render-inspect <patch_or_module> [--t 1.0] [--output /tmp/frame.png] [--width 800] [--height 600]"
user-invocable: true
---

# /render-inspect

Render a patch or module using the headless renderer and return comprehensive frame analysis.

## Instructions

Parse the user's arguments. Defaults: `--t 1.0`, `--width 800`, `--height 600`, no `--output`.

The first positional argument is either:
- A **patch path** like `projects.demo.demo_audio_file` or `.oblique.repl_patch:temp_patch` (module path with optional `:function` suffix)
- A **module class name** like `PolkaDotsModule` (will be auto-discovered from the registry)

Write and execute a Python script in `/tmp/oblique_render_inspect.py` that does the following:

```python
import sys, json, importlib
sys.path.insert(0, "/Users/juliendreux/Documents/dev/oblique")

import numpy as np
import moderngl
from core import renderer as oblique_renderer
from core.frame_analysis import analyze_frame

# --- Setup ---
WIDTH, HEIGHT = <width>, <height>
T = <t>
OUTPUT = <output_path or None>

ctx = moderngl.create_context(standalone=True)
oblique_renderer.set_ctx(ctx)

# --- Load and render ---
# If it's a patch path: import the module, call the factory function
# If it's a module class name: discover from registry, create with default params

# For patch: use the same logic as cli.py PatchRef
# For module: from core.registry import discover_modules; find the class; instantiate with minimal params

module_or_patch = ...  # resolve from args
# If it's an ObliquePatch, call .tick(T) to get the module
# Then call module.render_texture(ctx, WIDTH, HEIGHT, T)

tex = module.render_texture(ctx, WIDTH, HEIGHT, T)
raw = tex.read()
arr = np.frombuffer(raw, dtype=np.float32).reshape(HEIGHT, WIDTH, 4)
arr = arr[::-1].copy()  # flip Y

# --- Analysis ---
frame_metrics = analyze_frame(arr)

# Per-channel stats
for i, ch in enumerate(["R", "G", "B", "A"]):
    channel = arr[:, :, i]
    print(f"{ch}: min={channel.min():.4f}  max={channel.max():.4f}  mean={channel.mean():.4f}  std={channel.std():.4f}")

# Alpha analysis
alpha = arr[:, :, 3]
total = alpha.size
fully_transparent = (alpha == 0).sum()
fully_opaque = (alpha >= 0.999).sum()
semi = total - fully_transparent - fully_opaque
print(f"\nAlpha: {fully_transparent/total*100:.1f}% transparent, {fully_opaque/total*100:.1f}% opaque, {semi/total*100:.1f}% semi-transparent")

# Flags
if alpha.min() > 0.99:
    print("⚠ Alpha is all 1.0 — this module does NOT produce transparency")
if frame_metrics.get("is_blank"):
    print("⚠ Frame is blank (all black)")
if frame_metrics.get("is_saturated"):
    print("⚠ Frame is saturated (mostly clipped to white)")
if frame_metrics.get("is_dark"):
    print("⚠ Frame is very dark")

print(f"\nFrame analysis: {json.dumps(frame_metrics, indent=2)}")

# Save if requested
if OUTPUT:
    from PIL import Image
    img = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8))
    img.save(OUTPUT)
    print(f"\nSaved to {OUTPUT}")
```

Adapt the script based on the actual arguments. Key patterns for loading:

**Patch path** (contains `.` or `:`):
```python
module_name, _, func_name = patch_arg.rpartition(":")
if not func_name:
    func_name = "patch"
mod = importlib.import_module(module_name)
factory = getattr(mod, func_name)
patch = factory(WIDTH, HEIGHT)
module = patch.tick(T)
```

**Module class name** (no dots):
```python
from core.registry import discover_modules, get_registry
discover_modules()
registry = get_registry()
entry = registry[class_name]
cls = entry["cls"]
# Build minimal params — just width + height, defaults for everything else
import dataclasses
params_cls = ... # get from cls type hints or the first generic arg
fields = dataclasses.fields(params_cls)
kwargs = {"width": WIDTH, "height": HEIGHT}
module = cls(params_cls(**kwargs))
```

After running the script, if `--output` was provided, use the Read tool to display the image to the user.

Report the results in a clean summary table format.
