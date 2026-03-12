# Oblique – Modular AV Synthesizer

Oblique is a Python-orchestrated, Shadertoy-style engine for real-time, audio-reactive
visuals. It targets artists who want to pair live music with live visuals and includes
bindings for external devices such as Elektron gear.

## How it Works

Oblique follows a simple flow: **Input → Processing → AV Modules → Output**

- **Input** – Audio files, live audio, MIDI, or time signals
- **Processing** – Feature extraction, normalization and event detection
- **AV Modules** – Fragment-shader based visual units with a registry of 20+ built-in modules
- **Output** – Real-time window or headless rendering to PNG/video

### AV Modules

Modules follow the Shadertoy rendering model: a stock vertex shader drives a
full-screen quad while the fragment shader contains the creative logic. Modules may
use ping-pong buffers for feedback and additional off-screen passes (`TexturePass`)
for intermediate compositing. All modules are registered via the `@oblique_module`
decorator and discoverable through the CLI.

### Patches

A **patch** is a small Python function that returns an `ObliquePatch` describing
the inputs and AV module to run. Here's a patch using the chain API:

```python
from core.oblique_patch import ObliquePatch
from inputs.audio.core.audio_file_input import AudioFileInput
from modules.audio_reactive.circle_echo import CircleEcho, CircleEchoParams
from modules.effects.blur_module import BlurModule
from modules.effects.feedback import Feedback
from processing.fft_bands import FFTBands

def patch(width, height):
    audio = AudioFileInput("beat.wav")
    fft = FFTBands(audio)
    circle = CircleEcho(CircleEchoParams(width=width, height=height), fft)

    # Chain API: pipe through effects fluently
    scene = (
        circle
        .to(BlurModule, radius=2.0)
        .to(Feedback, decay=0.92)
    )

    def tick(t: float):
        return scene

    return ObliquePatch(audio_output=audio, tick_callback=tick)
```

## Key Features

- **Chain API** – Compose modules fluently with `.to()` and `.mix()` instead of nested constructors
- **Module Registry** – 20+ built-in modules discoverable via `oblique list-modules` and `oblique describe`
- **Headless Rendering** – Export single frames, PNG sequences, or video via `oblique render`
- **Frame Analysis** – Diagnostic metrics (brightness, color, motion, perceptual hashing) for rendered output
- **Audio-reactive** analysis and feature extraction
- **Hardware integration** with external devices (e.g. Elektron gear)
- **Hot reload** – Live shader editing with automatic error recovery (falls back to last good shader)
- **Debug mode** – `--debug` reports extra/missing uniforms at runtime
- **GPU-native** GLSL rendering with LRU texture caching
- **Performance** – 60 FPS @ 1080p on Apple Silicon

## Quick Start

```bash
# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Oblique
pip install --editable .

# List available modules
oblique list-modules

# Describe a module
oblique describe CircleEcho

# Launch a demo patch
oblique start projects.demo.demo_audio_file

# Headless render a single frame
oblique render projects.demo.demo_audio_file --t 1.0 --output /tmp/frame.png

# Render with frame analysis stats
oblique render projects.demo.demo_audio_file --t 1.0 --inspect

# Export a video
oblique render projects.demo.demo_audio_file --duration 3 --fps 30 --output /tmp/preview.mp4

# Launch with options
oblique start projects.demo.demo_audio_file --width 1920 --height 1080 --fps 60 --hot-reload-shaders

# Start a REPL workspace with hot reload
oblique start repl --hot-reload-shaders --hot-reload-python

# Custom factory function
oblique start my_project.live:build_patch
```

## Current Limitations

- Optimised for Apple Silicon with Metal-backed OpenGL
- Requires GLSL **330 core** shaders
- No cross-platform support at the moment

## Audio Input

Audio sources are configured inside project files. Helper utilities make
device discovery straightforward:

```python
from inputs.audio.core import audio_device_like

# Create an AudioDeviceInput from the first device whose name matches the pattern
audio_input = audio_device_like("Digitakt")
```

`AudioDeviceInput` captures from a live audio device or interface. For file-based
audio, use `AudioFileInput`:

```python
from inputs.audio.core.audio_file_input import AudioFileInput

audio = AudioFileInput("path/to/beat.wav", chunk_size=1024)
```

## Modules

Modules are self-contained Python classes inheriting from `BaseAVModule`, each
paired with a GLSL fragment shader. All modules are decorated with `@oblique_module`
for registry discovery.

### Shader Loader & Includes

Shaders are preprocessed before compilation using a lightweight loader that resolves
`#include` directives. Includes can point to other files in `shaders/` using
`#include "path/to/file.glsl"` or pull from the vendored [LYGIA](https://github.com/patriciogonzalezvivo/lygia)
library via `#include <lygia/path/to/file.glsl>`.

## MIDI Input

`MidiInput` captures real-time MIDI messages using `mido`. It buffers note and control events
and listens for transport commands such as clock and start/stop to track playback state and
estimate tempo.

## Testing

```bash
pip install -r requirements.txt
pytest
pytest --cov  # with coverage
```

## Repository Structure

```
oblique/
├── cli.py         # CLI entry point (start, render, list-modules, describe)
├── core/          # Engine loop, renderer, registry, frame analysis, patch definitions
├── inputs/        # Audio, MIDI, and device input sources
├── modules/       # AV modules paired with GLSL shaders
├── processing/    # Signal processing operators
├── shaders/       # Shared GLSL snippets
├── external/      # Third-party resources (e.g. vendored LYGIA shader library)
├── projects/      # Example patches and experiments
├── docs/          # Design documents and backlog
├── tests/         # Test suite
├── pyproject.toml # Packaging metadata and CLI entry points
└── README.md
```
