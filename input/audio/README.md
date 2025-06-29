# Audio Input for Oblique

This module provides audio file playback and real-time analysis for the Oblique AV synthesizer.

## Features

- **Audio File Support**: Load and play WAV, FLAC, MP3, and other audio formats
- **Real-time Analysis**: Extract amplitude, envelope, peak, and FFT data
- **Threaded Playback**: Non-blocking audio playback in separate thread
- **Audio Reactivity**: Provide audio data to visual modules for reactive effects

## Usage

### Command Line

```bash
# Run with audio file
python main.py --audio path/to/your/audio.wav

# Customize parameters
python main.py --audio music.wav --audio-sensitivity 5.0 --grid-size 30.0
```

### Programmatic

```python
from input.audio.audio_player import AudioPlayer

# Create audio player
player = AudioPlayer("path/to/audio.wav")

# Start playback
player.start_playback()

# Get audio data
audio_data = player.get_audio_data()
print(f"Amplitude: {audio_data['amplitude']}")
print(f"Envelope: {audio_data['env']}")
print(f"Peak: {audio_data['peak']}")
```

## Audio Data Format

The audio player provides the following data structure:

```python
{
    'fft': [float, ...],      # 64-band FFT magnitude spectrum
    'env': float,             # Smoothed envelope follower
    'peak': float,            # Peak amplitude
    'amplitude': float,       # RMS amplitude
    'is_playing': bool,       # Playback status
    'position': float,        # Current position in seconds
    'duration': float         # Total duration in seconds
}
```

## Supported Formats

- WAV
- FLAC
- OGG
- AIFF
- And other formats supported by `soundfile`

## Dependencies

- `soundfile`: Audio file reading
- `numpy`: Audio processing
- `threading`: Non-blocking playback

## Integration with Visual Modules

Visual modules receive audio data through the `update()` method:

```python
def update(self, audio_data: Dict[str, Any], time_data: Dict[str, Any]):
    amplitude = audio_data['amplitude']
    envelope = audio_data['env']
    peak = audio_data['peak']
    
    # Make visuals reactive to audio
    intensity = envelope * self.audio_sensitivity
    # ... use intensity in shader uniforms
``` 