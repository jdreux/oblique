import argparse

# --- Core imports ---
from core import ObliqueEngine, ObliquePatch
from inputs.audio_device_input import AudioDeviceInput, print_audio_devices

# --- Input imports ---
from inputs.audio_file_input import AudioFileInput
from inputs.base_input import BaseInput

# --- Module imports ---
from modules.circle_echo import CircleEcho, CircleEchoParams
from modules.debug import DebugModule, DebugParams
from modules.feedback import Feedback, FeedbackParams
from modules.iked_grid import IkedGrid, IkedGridParams
from modules.ikeda_test_pattern import IkedaTestPatternModule, IkedaTestPatternParams
from modules.ikeda_tiny_barcode import IkedaTinyBarcodeModule, IkedaTinyBarcodeParams
from modules.mesh_shroud import MeshShroudModule, MeshShroudParams
from modules.ryoji_grid import RyojiGrid, RyojiGridParams
from modules.ryoji_lines import RyojiLines, RyojiLinesParams
from modules.shader_toy_tester import ShaderToyTesterModule
from modules.spectral_visualizer import (
    SpectralVisualizerModule,
    SpectralVisualizerParams,
)
from modules.transform import TransformModule, TransformParams
from modules.visual_noise import VisualNoiseModule, VisualNoiseParams
from processing.fft_bands import FFTBands
from processing.normalized_amplitude import NormalizedAmplitudeOperator
from processing.spectral_centroid import SpectralCentroid


def create_demo_patch(width: int, height: int, audio_input: BaseInput) -> ObliquePatch:
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

    # audio_input = AudioFileInput(file_path=audio_path)

    patch.input(audio_input)
    amplitude_processor = NormalizedAmplitudeOperator(audio_input)
    debug_module = DebugModule(
        DebugParams(width=width, height=height, number=0.0, text="Debug"),
        amplitude_processor,
    )
    # patch.add(debug_module)

    fft_bands_processor16 = FFTBands(audio_input, perceptual=True, num_bands=16)
    ryoji_grid_module = RyojiGrid(RyojiGridParams(width=width, height=height))
    circle_echo_module = CircleEcho(
        CircleEchoParams(width=width, height=height, n_circles=32),
        fft_bands_processor16,
    )

    spectral_centroid_processor = SpectralCentroid(audio_input)
    fft_bands_processor512 = FFTBands(audio_input, perceptual=True, num_bands=512)
    fft_bands_processor64 = FFTBands(audio_input, perceptual=True, num_bands=64)
    ryoji_lines_module = RyojiLines(
        RyojiLinesParams(width=width, height=height, num_bands=2**7),
        fft_bands_processor512,
        spectral_centroid_processor,
    )
    visual_noise_module = VisualNoiseModule(
        VisualNoiseParams(width=width, height=height, color_mode="rgba", noise_size="large", speed=0.1)
    )
    ikeda_test_pattern = IkedaTestPatternModule(
        IkedaTestPatternParams(width=width, height=height), module=circle_echo_module
    )
    ikeda_tiny_barcode_module = IkedaTinyBarcodeModule(
        IkedaTinyBarcodeParams(width=width, height=height), fft_bands_processor512
    )
    spectral_visualizer_module = SpectralVisualizerModule(
        SpectralVisualizerParams(width=width, height=height), fft_bands_processor512
    )

    mesh_module = MeshShroudModule(
        MeshShroudParams(width=width, height=height), fft_bands_processor64, amplitude_processor
    )

    shader_toy_tester = ShaderToyTesterModule()

    # Create IkedGrid module that creates its own pattern and swaps squares
    iked_grid_module = IkedGrid(
        IkedGridParams(
            width=width,
            height=height,
            grid_size=3,
            swap_frequency=2.0,  # Increased frequency for more visible swaps
            swap_phase=0.0,
            num_swaps=4,
        ),
        module=circle_echo_module,
    )

    # Add feedback module with spectral visualizer as input
    feedback_module = Feedback(
        FeedbackParams(
            width=width,
            height=height,
            feedback_strength=0.95,
            reset_on_start=True,
        ),
        upstream_module=mesh_module,
    )

    # Test transform module
    transform_module = TransformModule(
        TransformParams(
            width=width,
            height=height,
            scale=(0.94, 0.78),
            angle=67,
            pivot=(0.7, 0.3),
            translate=(0.05, -0.5),
            transform_order="SRT",
        ),
        upstream_module=feedback_module,
    )

    # patch.add(shader_toy_tester)  # Test feedback module with input
    # patch.add(spectral_visualizer_module)
    patch.add(feedback_module)  # Test transform module
    return patch


def main():
    """Main entry point for Oblique MVP."""
    parser = argparse.ArgumentParser(description="Oblique MVP - Minimal AV Synthesizer")
    parser.add_argument("--width", type=int, default=800, help="Window width")
    parser.add_argument("--height", type=int, default=600, help="Window height")
    parser.add_argument(
        "--audio-file",
        type=str,
        default=None,
        help="Path to audio file for playback (or 'device' for real-time input)",
    )
    parser.add_argument(
        "--audio-device",
        type=int,
        default=None,
        help="Audio device ID to use for real-time input",
    )
    parser.add_argument(
        "--audio-channels",
        type=str,
        default=None,
        help="Comma-separated list of channel indices to capture (e.g., '0,1' for stereo)",
    )
    parser.add_argument(
        "--list-audio-devices",
        action="store_true",
        help="List available audio input devices and exit",
    )
    parser.add_argument("--fps", type=int, default=60, help="Target frame rate")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with performance monitoring",
    )
    parser.add_argument(
        "--monitor",
        type=int,
        default=None,
        help="Monitor index to open window on (use --list-monitors to see available monitors)",
    )
    parser.add_argument("--list-monitors", action="store_true", help="List available monitors and exit")
    args = parser.parse_args()

    # List monitors if requested
    if args.list_monitors:
        ObliqueEngine.list_monitors()
        return

    # List audio devices if requested
    if args.list_audio_devices:
        print_audio_devices()
        return

    # Parse audio channels if specified
    audio_channels = None
    if args.audio_channels:
        try:
            audio_channels = [int(ch.strip()) for ch in args.audio_channels.split(",")]
        except ValueError:
            print("Error: audio-channels must be comma-separated integers (e.g., '0,1')")
            return

    if args.audio_device is not None:
        audio_input = AudioDeviceInput(device_id=args.audio_device, channels=audio_channels)
    elif args.audio_file:
        audio_input = AudioFileInput(file_path=args.audio_file)
    else:
        print("Error: No audio input specified")
        return

    # Create the patch
    patch = create_demo_patch(args.width, args.height, audio_input)

    # Create and run the engine
    engine = ObliqueEngine(
        patch=patch,
        width=args.width,
        height=args.height,
        title="Oblique MVP",
        target_fps=args.fps,
        debug=args.debug,
        monitor=args.monitor,
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
