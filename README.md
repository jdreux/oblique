# Oblique - Modular AV Synthesizer

A minimal, shader-driven AV synthesizer focused on modularity, real-time performance, and audio-reactive visuals.

## Architecture

Oblique follows a clean architecture: **Input → Processing → Rendering → Output**

- **Input**: Raw audio, MIDI, OSC, time signals
- **Processing**: Feature extraction, normalization, event detection
- **Rendering**: Modular shader units with type-safe uniforms
- **Output**: Real-time audiovisual composition

## Key Features

- **Type-Safe Uniforms**: Dataclass-based uniform contracts prevent shader errors
- **State flows in one direction**: data flows down and defines state, REACT style approach. 
- **Audio-Reactive**: Real-time audio analysis and feature extraction
- **Modular Design**: Easy to create new visual modules
- **GPU-Native**: All visuals rendered via GLSL shaders
- **Performance**: 60 FPS @ 1080p on Apple Silicon

## Quick Start

```bash
# Install dependencies
./install.sh

# Run with demo audio
./start.sh

# Or run manually
python main.py --audio "path/to/audio.wav" --width 800 --height 600 --audio "path_to_audio"
```

## Folder struture 
/oblique/
├── main.py                    # Launches the engine and test modules
├── core/                      # Engine loop, base module interface
│   ├── engine.py             # Main AV engine (composition, routing)
│   ├── base_module.py        # Base class for rendering modules
│   └── signal_processor.py   # Signal processing and normalization
├── input/                     # Raw signal collection
│   ├── audio/                # Audio input and FFT analysis
│   ├── midi/                 # MIDI input (future)
│   └── osc/                  # OSC input (future)
├── processing/                # Signal processing and feature extraction
│   ├── audio_features.py     # FFT, envelope, peak detection
│   ├── signal_normalizer.py  # Normalize various input types
│   └── event_detector.py     # Beat detection, triggers
├── modules/                   # Visual rendering modules
│   └── animated_grid.py      # Example module
├── shaders/                   # GLSL fragment shaders for modules
├── output/                    # Final composition and delivery
│   ├── compositor.py         # Module blending and composition
│   └── display.py            # Window, Syphon, recording
├── install.sh                 # Dependency installation
├── start.sh                   # Starts a run with default settings
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

Example:
```python
class FlickerGrid(BaseAVModule):
    def update(processed_signals, time_data):
        # Update module state based on processed signals
        ...
    def render():
        # Render to framebuffer
        return framebuffer
```

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