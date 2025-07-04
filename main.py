import argparse
from pathlib import Path

# --- Core imports ---
from core import ObliqueEngine, ObliquePatch

# --- Module imports ---
from modules import ryoji_grid
from modules.ryoji_grid import RyojiGrid, RyojiGridParams
from modules.pauric_particles import PauricParticles, PauricParticlesParams
from modules.circle_echo import CircleEcho, CircleEchoParams
from modules.debug import DebugModule, DebugParams
from processing.normalized_amplitude import NormalizedAmplitudeOperator
from processing.fft_bands import FFTBands
# --- Input imports ---
from inputs.audio_device_input import AudioDeviceInput
from modules.ryoji_lines import RyojiLines, RyojiLinesParams
from processing.spectral_centroid import SpectralCentroid

def create_demo_patch(width: int, height: int, audio_path: str) -> ObliquePatch:
    """
    Create a demo patch with some example modules.
    This function can be easily modified to create different patch configurations.
    
    Args:
        width: Window width
        height: Window height
        
    Returns:
        Configured ObliquePatch instance
    """
    patch = ObliquePatch()

    audio_input = AudioDeviceInput(file_path=audio_path)

    patch.input(audio_input)
    amplitude_processor = NormalizedAmplitudeOperator(audio_input)
    # debug_module = DebugModule(DebugParams(width=width, height=height, number=0.0, text="Debug"), amplitude_processor)
    # patch.add(debug_module)

    fft_bands_processor = FFTBands(audio_input, perceptual=True, num_bands=512)
    spectral_centroid_processor = SpectralCentroid(audio_input)

    # ryoji_grid_module = RyojiGrid(RyojiGridParams(width=width, height=height), fft_bands_processor)
    # circle_echo_module = CircleEcho(CircleEchoParams(width=width, height=height), fft_bands_processor)
    ryoji_lines_module = RyojiLines(RyojiLinesParams(width=width, height=height, num_bands=512), fft_bands_processor, spectral_centroid_processor)
    patch.add(ryoji_lines_module)
    
    
    return patch


def main():
    """Main entry point for Oblique MVP."""
    parser = argparse.ArgumentParser(description="Oblique MVP - Minimal AV Synthesizer")
    parser.add_argument('--width', type=int, default=800, help='Window width')
    parser.add_argument('--height', type=int, default=600, help='Window height')
    parser.add_argument('--audio', type=str, default=None, help='Path to audio file for playback')
    parser.add_argument('--fps', type=int, default=60, help='Target frame rate')
    args = parser.parse_args()

    # Create the patch
    patch = create_demo_patch(args.width, args.height, args.audio)
    
    # Create and run the engine
    engine = ObliqueEngine(
        patch=patch,
        width=args.width,
        height=args.height,
        title="Oblique MVP",
        target_fps=args.fps
    )
    
    try:
        engine.run()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    main() 