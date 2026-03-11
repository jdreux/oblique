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

# Launch a patch
oblique start projects.demo.demo_audio_file

# Launch with options
oblique start projects.demo.demo_audio_file --width 1920 --height 1080 --fps 60 --hot-reload-shaders

# Start REPL (creates .oblique/repl_patch.py, supports Python hot reload)
oblique start repl --hot-reload-shaders --hot-reload-python

# Dry run to inspect config without launching
oblique start projects.demo.demo_audio_file --dry-run

# Custom factory function (module:function syntax)
oblique start my_project.live:build_patch
```

## Architecture

Data flows unidirectionally: **Input → Processing → AV Module → Output**

### Core Components

- **`ObliquePatch`** (`core/oblique_patch.py`) – User-authored descriptor that wires inputs, processors, and modules together. It holds a `tick_callback(t: float) -> BaseAVModule` called every frame.
- **`ObliqueEngine`** (`core/oblique_engine.py`) – Main runtime loop: creates the GLFW/OpenGL window, drives the frame loop, manages audio playback on a background thread.
- **`BaseAVModule`** (`modules/core/base_av_module.py`) – Abstract base for all visual units. Subclasses implement `prepare_uniforms(t)` and declare `frag_shader_path`. The base class handles `TexturePass` dependency resolution, ping-pong buffering, and calling `core.renderer.render_to_texture`.
- **`TexturePass`** – Declarative off-screen pass descriptor. Nest them in `prepare_uniforms` uniforms to build multi-pass pipelines; the framework resolves them depth-first each frame.
- **`BaseProcessingOperator`** (`processing/base_processing_operator.py`) – Generic operator that reads from an audio input and produces a typed value via `process()`. Used as live shader parameters.

### Module Parameters

Module params are typed dataclasses extending `BaseAVParams` (which requires `width` and `height`). Parameters can be static values, callables, or `BaseProcessingOperator` instances—`_resolve_param()` handles all three at render time.

### Shader System

- Shaders live alongside their module in `modules/<category>/shaders/` or in `shaders/` for shared snippets.
- The preprocessor (`core/shader_preprocessor.py`) resolves `#include "path"` and `#include <lygia/...>` directives before compilation.
- All shaders must start with `#version 330 core`.
- GLSL uniform names must match the keys returned by `prepare_uniforms` (prefixed with `u_` automatically if missing).
- `u_resolution` is injected automatically.

### Creating a New Module

1. Create `modules/<category>/my_module.py` with a `MyParams(BaseAVParams)` dataclass and a `MyModule(BaseAVModule[MyParams, MyUniforms])` class.
2. Implement `prepare_uniforms(self, t: float) -> MyUniforms` returning a dict of uniform values.
3. Set `frag_shader_path` as a class attribute pointing to the `.frag` file.
4. Create the GLSL shader at `modules/<category>/shaders/my_module.frag`.
5. Add `metadata = {"name": ..., "description": ..., "parameters": {...}}` to the class.

See `modules/audio_reactive/circle_echo.py` as a minimal reference.

### Inputs

All inputs extend `BaseInput` (`inputs/base_input.py`) with `start()`, `stop()`, `read()`, `peek()`.

- **`AudioFileInput`** – reads a WAV/audio file.
- **`AudioDeviceInput`** – captures from a live audio device; use `audio_device_like("Digitakt")` for fuzzy name matching.
- **`MidiInput`** – real-time MIDI via `mido`, buffers note/CC events, tracks transport state.

### Code Conventions

- PEP 8, lines ≤ 100 characters (ruff configured in `pyproject.toml`).
- Strong typing throughout; use dataclasses for all parameter objects.
- Prefer absolute imports.
- `patch` factory functions always have signature `(width: int, height: int) -> ObliquePatch` — the engine passes `width * 2` / `height * 2` internally for Retina displays.
- macOS / Apple Silicon only; GLSL 330 required.
