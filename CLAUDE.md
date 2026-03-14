# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install --editable .
```

## Commands

```bash
# Unit tests (stubs, no GPU)
pytest

# GPU/headless tests — run in isolation (stubs from unit tests pollute sys.modules)
pytest tests/test_headless_renderer.py -v

# Run with coverage
pytest --cov

# Headless render — single frame (for AI agent verification)
oblique render projects.demo.demo_audio_file --t 1.0 --output /tmp/frame.png

# Headless render — print stats without saving
oblique render projects.demo.demo_audio_file --t 1.0 --inspect

# Headless render — PNG sequence (time sweep)
oblique render projects.demo.demo_audio_file --duration 3 --fps 10 --output-dir /tmp/frames/

# Headless render — video (requires ffmpeg)
oblique render projects.demo.demo_audio_file --duration 3 --fps 30 --output /tmp/preview.mp4

# List all registered modules
oblique list-modules
oblique list-modules --json --tag audio-reactive --category effects

# Describe a specific module
oblique describe CircleEcho
oblique describe CircleEcho --json

# Launch a patch
oblique start projects.demo.demo_audio_file

# Launch with options
oblique start projects.demo.demo_audio_file --width 1920 --height 1080 --fps 60 --hot-reload-shaders

# Live mode — TUI control surface + file watching + hot reload (preferred)
oblique live
oblique live projects.demo.demo_audio_file
oblique live --width 1920 --height 1080 --no-hot-reload-python

# Start REPL (deprecated — redirects to `oblique live`)
oblique start repl

# Dry run to inspect config without launching
oblique start projects.demo.demo_audio_file --dry-run

# Debug mode — reports extra/missing uniforms at runtime
oblique start projects.demo.demo_audio_file --debug
oblique render projects.demo.demo_audio_file --t 1.0 --debug --inspect

# Custom factory function (module:function syntax)
oblique start my_project.live:build_patch
```

## Architecture

Data flows unidirectionally: **Input → Processing → AV Module → Output**

### Core Components

- **`ObliquePatch`** (`core/oblique_patch.py`) – User-authored descriptor that wires inputs, processors, and modules together. It holds a `tick_callback(t: float) -> BaseAVModule` called every frame.
- **`ObliqueEngine`** (`core/oblique_engine.py`) – Main runtime loop: creates the GLFW/OpenGL window, drives the frame loop, manages audio playback on a background thread.
- **`BaseAVModule`** (`modules/core/base_av_module.py`) – Abstract base for all visual units. Subclasses implement `prepare_uniforms(t)` and declare `frag_shader_path`. The base class handles `TexturePass` dependency resolution, ping-pong buffering, LRU texture caching, and calling `core.renderer.render_to_texture`.
- **`TexturePass`** – Declarative off-screen pass descriptor. Nest them in `prepare_uniforms` uniforms to build multi-pass pipelines; the framework resolves them depth-first each frame. Supports `inherit_parent_uniforms` (default `True`) to opt in/out of receiving parent uniforms.
- **`BaseProcessingOperator`** (`processing/base_processing_operator.py`) – Generic operator that reads from an audio input and produces a typed value via `process()`. Used as live shader parameters.

### Module Registry

Modules are registered via the `@oblique_module` decorator (`core/registry.py`). The decorator attaches metadata and enables discovery via `oblique list-modules` and `oblique describe`.

```python
from core.registry import oblique_module

@oblique_module(
    category="audio_reactive",
    description="Draws concentric circles whose modulation responds to audio bands.",
    tags=["geometric", "audio-reactive", "pulsing", "rhythmic"],
    cost_hint="medium",
)
class CircleEcho(BaseAVModule[CircleEchoParams, CircleEchoUniforms]):
    ...
```

`discover_modules()` walks the `modules/` package tree to find all decorated classes.

### Chain API

Modules can be composed fluently using `.to()` and `.mix()` on any `BaseAVModule`:

- **`.to(ModuleClass, **kwargs)`** – Pipes this module's output texture into the first `ParamTexture` / `BaseAVModule` field of the target module. `width` and `height` are inherited automatically.
- **`.mix(other, amount=0.5, op=CompositeOp.SCREEN)`** – Blends this module with another via `CompositeModule`. Returns a `BaseAVModule`, so chains can continue.

```python
result = (
    source
    .to(BlurModule, radius=4.0)
    .to(LevelModule, brightness=1.2)
    .mix(background, amount=0.5, op=CompositeOp.ADD)
    .to(Feedback, decay=0.95)
)
```

Prefer `.to()` / `.mix()` over manually constructing nested params.

### Headless Renderer

`core/headless_renderer.py` provides GPU rendering without a window (EGL/osmesa context). Used by `oblique render` for single frames, PNG sequences, and video export. Supports `--inspect` to print frame analysis stats without saving.

### Frame Analysis

`core/frame_analysis.py` provides diagnostic metrics for rendered frames:

- **`analyze_frame(arr)`** – Returns brightness, color, saturation, edge density, spatial balance, and boolean flags (`is_blank`, `is_saturated`, `is_dark`, `has_color`).
- **`analyze_temporal(frames)`** – Motion metrics across a sequence (`mean_motion`, `is_static`, `is_chaotic`).
- **`perceptual_hash(arr)`** / **`hash_distance(h1, h2)`** – Bitstring hashing for frame similarity.

### Module Parameters

Module params are typed dataclasses extending `BaseAVParams` (which requires `width` and `height`). Parameters can be static values, callables, or `BaseProcessingOperator` instances—`_resolve_param()` handles all three at render time.

### Shader System

- Shaders live alongside their module in `modules/<category>/shaders/` or in `shaders/` for shared snippets.
- The preprocessor (`core/shader_preprocessor.py`) resolves `#include "path"` and `#include <lygia/...>` directives before compilation.
- All shaders must start with `#version 330 core`.
- GLSL uniform names must match the keys returned by `prepare_uniforms`. All uniform keys must use the explicit `u_` prefix.
- `u_resolution` is injected automatically.

### Shader Error Recovery

When a shader fails to compile (e.g. during hot-reload), the renderer falls back to the last successfully compiled version of that shader. This prevents black screens during live editing. The fallback is logged as a warning. If no previous good version exists, the error propagates normally.

### Texture Cache

The renderer maintains an LRU texture cache (`OrderedDict`, max 64 entries). Textures are keyed by module class, cache tag, dimensions, and filter mode. Least-recently-used textures are evicted and released when the cache exceeds capacity.

### Debug Mode

Enable with `--debug` on `start` or `render` commands, or call `set_debug_mode(True)` from `core.renderer`. When active, the renderer reports:
- Extra uniforms provided by Python but not consumed by the shader
- Missing uniforms expected by the shader but not provided by Python

### Creating a New Module

1. Create `modules/<category>/my_module.py` with a `MyParams(BaseAVParams)` dataclass and a `MyModule(BaseAVModule[MyParams, MyUniforms])` class.
2. Decorate the class with `@oblique_module(category=..., description=..., tags=[...], cost_hint=...)`.
3. Implement `prepare_uniforms(self, t: float) -> MyUniforms` returning a dict of uniform values (all keys must use the `u_` prefix).
4. Set `frag_shader_path` as a class attribute pointing to the `.frag` file.
5. Create the GLSL shader at `modules/<category>/shaders/my_module.frag`.
6. Ensure the module works with the chain API — include a `ParamTexture` / `BaseAVModule` field in your params if the module accepts a texture input.

See `modules/audio_reactive/circle_echo.py` as a minimal reference.

### Live Mode (`oblique live`)

Two-process architecture for live performance:

- **Process A (main thread):** GLFW render window + OpenGL, audio thread, file watchers, MIDI polling.
- **Process B (subprocess):** Textual TUI in the terminal — param sliders, telemetry bar, error log, status footer.
- **IPC:** `multiprocessing.Pipe` with a background sender thread (never blocks the render loop).

Key files:
- **`live.py`** — Entry point. Loads patch, creates engine, spawns TUI, wires IPC, runs render loop.
- **`core/control_ipc.py`** — `ControlBridge`: engine-side IPC bridge. Sends telemetry (~10Hz), param snapshots, log messages. Receives `set_param`/`reload`/`quit` from TUI. Duck-type compatible with old `ControlWindow` via `mark_dirty()`.
- **`core/control_tui.py`** — Textual `App` subclass. Polls IPC at 20Hz, rebuilds sliders dynamically on `params_snapshot`, routes `ParamBar.Changed` back as `set_param`.
- **`core/control_subprocess.py`** — `spawn_control_tui(store)` → `(ControlBridge, Process)`. Reopens `/dev/tty` in the subprocess so Textual can drive the terminal.
- **`core/param_store.py`** — `ParamStore` with `_on_change` callback. Wired to `bridge.send_param_update` so MIDI/code changes auto-forward to TUI.
- **`core/logger.py`** — `set_log_sink(callback)` forwards all log messages to the TUI log panel.

`oblique live` defaults: `--hot-reload-shaders` and `--hot-reload-python` are **on** by default (use `--no-hot-reload-*` to disable). Console logging is suppressed (TUI owns the terminal); parent stdout/stderr redirected to `/dev/null`.

### Inputs

All inputs extend `BaseInput` (`inputs/base_input.py`) with `start()`, `stop()`, `read()`, `peek()`.

- **`AudioFileInput`** (`inputs.audio.core.audio_file_input`) – Reads WAV/FLAC/AIFF/OGG files. Constructor: `AudioFileInput(file_path, chunk_size=1024)`.
- **`AudioDeviceInput`** (`inputs.audio.core.audio_device_input`) – Captures from a live audio device. Constructor: `AudioDeviceInput(device_id=None, channels=None, samplerate=44100, chunk_size=256)`. Use `audio_device_like("Digitakt")` for fuzzy name matching.
- **`MidiInput`** (`inputs.midi.core.midi_input`) – Real-time MIDI via `mido`, buffers note/CC events, tracks transport state.

### Code Conventions

- PEP 8, lines ≤ 100 characters (ruff configured in `pyproject.toml`).
- Strong typing throughout; use dataclasses for all parameter objects.
- Prefer absolute imports.
- Prefer `.to()` / `.mix()` over nested module constructors.
- Prefer adding new modules over modifying the core engine.
- `patch` factory functions always have signature `(width: int, height: int) -> ObliquePatch` — the engine passes `width * 2` / `height * 2` internally for Retina displays.
- macOS / Apple Silicon only; GLSL 330 required.
- Target 60 FPS at 1080p; avoid blocking CPU calls and large CPU↔GPU transfers.

### New Module Checklist

- [ ] `@oblique_module` decorator with `category`, `description`, `tags`, `cost_hint`
- [ ] `Params` dataclass extending `BaseAVParams`
- [ ] `prepare_uniforms(t)` returning typed dict (all keys with `u_` prefix)
- [ ] `frag_shader_path` class attribute
- [ ] GLSL shader in `modules/<category>/shaders/`
- [ ] `ParamTexture` field if module accepts texture input (chain API compatibility)
