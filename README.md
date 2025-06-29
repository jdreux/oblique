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
python main.py --audio "path/to/audio.wav" --width 800 --height 600
```

## Creating Modules

Oblique uses a **dataclass-based uniform system** to prevent shader errors. Here's how to create a new module:

### 1. Define Your Uniforms

```python
from dataclasses import dataclass
from core.base_module import BaseAVModule, BaseUniforms

@dataclass
class MyModuleUniforms(BaseUniforms):
    """Uniforms for your shader - must match GLSL declarations exactly."""
    scale: float = 1.0
    color: tuple[float, float, float] = (1.0, 0.0, 0.0)
    audio_intensity: float = 0.0
```

### 2. Create Your Module

```python
class MyModule(BaseAVModule):
    def get_uniforms_class(self):
        return MyModuleUniforms
    
    def get_metadata(self):
        return {
            'name': 'MyModule',
            'description': 'My awesome module',
            'shader_file': 'my-module.frag',
            'category': 'pattern'
        }
    
    def update(self, processed_signals, time_data):
        # Update uniforms safely - no more 'audio_energy' errors!
        self.update_uniforms(
            time=time_data['time'],
            scale=1.0 + processed_signals['audio']['envelope'],
            color=self.props.get('color', (1, 0, 0)),
            audio_intensity=processed_signals['audio']['envelope']
        )
```

### 3. Create Your Shader

```glsl
#version 330

uniform float time;
uniform vec2 resolution;
uniform float scale;
uniform vec3 color;
uniform float audio_intensity;

in vec2 uv;
out vec4 fragColor;

void main() {
    // Your shader code here
    vec2 pos = uv * resolution * scale;
    float intensity = audio_intensity * sin(time);
    fragColor = vec4(color * intensity, 1.0);
}
```

## Benefits of the Dataclass System

✅ **Type Safety**: Python types ensure correct uniform specifications  
✅ **No Runtime Errors**: Impossible to set non-existent uniforms  
✅ **Self-Documenting**: Clear contract between Python and GLSL  
✅ **IDE Support**: Autocomplete and type checking  
✅ **Validation**: Automatic shader validation at startup  

## Project Structure

```
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
├── config/                    # Engine settings, presets
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
- Linked to a GLSL shader for rendering
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