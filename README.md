# Oblique – Modular AV Synthesizer

Oblique is a Python‑orchestrated, Shadertoy‑style engine for real‑time, audio‑reactive
visuals.  It targets artists who want to pair live music with live visuals and includes
bindings for external devices such as Elektron gear.

## How it Works

Oblique follows a simple flow: **Input → Processing → AV Modules → Output**

- **Input** – Audio files, live audio, MIDI, OSC, or time signals
- **Processing** – Feature extraction, normalization and event detection
- **AV Modules** – Fragment‑shader based visual units
- **Output** – Real‑time composition rendered to the screen

### AV Modules

Modules loosely follow the Shadertoy rendering model: a stock vertex shader drives a
full‑screen quad while the fragment shader contains the creative logic.  Modules may
optionally use ping‑pong buffers for feedback and additional off‑screen passes for
intermediate compositing.

### Patches

Most of the magic lives in a **patch** – a small Python function that returns an
`ObliquePatch` describing the inputs and AV module to run.  Here's a tiny patch that
plays an audio file while rendering a beat‑reactive circle:

```python
from core.oblique_patch import ObliquePatch
from inputs.audio_file_input import AudioFileInput
from modules.audio_reactive.circle_echo import CircleEcho, CircleEchoParams
from processing.fft_bands import FFTBands

def circle_patch(width, height):
    audio = AudioFileInput("beat.wav")
    fft = FFTBands(audio)
    circle = CircleEcho(CircleEchoParams(width=width, height=height), fft)

    def tick(t: float):
        return circle

    return ObliquePatch(audio_output=audio, tick_callback=tick)
```

Save this as `circle_patch.py` and wire it up in your own runner or modify `main.py` to
load the patch.

## Key Features

- **One‑way state flow**: data flows downward, fully in code.
- **Audio‑reactive** analysis and feature extraction
- **Modular design** for creating new visual units
- **Hardware integration** with external devices (e.g. Elektron gear out of the box)
- **GPU‑native** GLSL rendering
- **Performance**: 60 FPS @ 1080p on Apple Silicon

## Current Limitations

- Optimised for Apple Silicon with Metal‑backed OpenGL
- Requires GLSL **330 core** shaders
- No cross‑platform support at the moment

## Quick Start

```bash
# Install dependencies
./install.sh

# Run with demo audio
./start.sh

# Or run manually
python main.py --audio "path/to/audio.wav" --width 800 --height 600 --audio "path_to_audio"
```


## Testing

This project uses [pytest](https://docs.pytest.org/) for unit testing.

```bash
pip install -r requirements.txt
pytest
```

Run with `pytest --cov` to measure test coverage.

## Repository Structure

```
oblique/
├── core/          # Engine loop, renderer and patch definitions
├── inputs/        # Audio and other data sources
├── modules/       # AV modules paired with GLSL shaders
├── processing/    # Signal processing operators
├── shaders/       # Shared GLSL snippets
├── external/      # Third-party resources
├── projects/      # Example patches and experiments
├── main.py        # Entry point loading an ObliquePatch
├── install.sh     # Dependency installation
├── start.sh       # Demo runner
└── README.md
```

---

## 🔊 Audio Input

We use the system microphone (or audio interface) via `sounddevice` to:
- Capture audio in real time, potentially from a file
- Perform FFT analysis
- Send normalized bands and envelope to the processing layer

---

## 🧩 Modules

Modules are:
- Self-contained Python classes inheriting from `BaseAVModule`
- Linked to a GLSL shader for rendering, where shaders are needed for perf.
- Driven by processed signals from the processing layer
- Easy to test independently


## 🤖 AI Agent Development

Oblique is designed to support AI-assisted and AI-authored development.

Modules and engine components follow simple, well-documented conventions that allow AI agents to:
- Generate new visual modules from template code
- Compose audio-reactive behaviors without deep engine knowledge
- Run, test, and swap modules programmatically

We optimize for:
- Predictable structure (one Python + one GLSL file per module)
- Clean metadata and parameter exposure
- Stateless components when possible
- Minimal dependencies and isolated functionality

Future goals include:
- AI-generated scenes and compositions
- Automatic module tuning from reference music or MIDI
- Generative documentation and mutation of existing patches

## Inputs

Inputs are modular sources of data for Oblique. All input classes inherit from `BaseInput` (in `/inputs/base_input.py`), which defines a simple interface: `start()`, `stop()`, and `read()`.

### Example: AudioDeviceInput

`AudioDeviceInput` reads audio from a file and provides it in chunks for processing and visualization. It is useful for prototyping and testing audio-reactive modules.

```python
from inputs.audio.core.audio_device_input import AudioDeviceInput
input_device = AudioDeviceInput("path/to/audio.wav", chunk_size=2048)
input_device.start()
chunk = input_device.read()
input_device.stop()
```

Future input modules will support live audio, MIDI, OSC, and more.
