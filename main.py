import argparse

# --- Core imports ---
from core import ObliqueEngine
from core.logger import configure_logging, debug, error, info
from inputs.audio_device_input import AudioDeviceInput, print_audio_devices

# --- Input imports ---
from inputs.audio_file_input import AudioFileInput
from projects.demo.shader_test import shader_test
from projects.demo.demo_audio_file import audio_file_demo_patch
from projects.demo.demo_syntakt import create_demo_syntakt


def main():
    """Main entry point for Oblique."""
    parser = argparse.ArgumentParser(description="Oblique - Minimal AV Synthesizer")
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
        default=False,
    )
    parser.add_argument(
        "--monitor",
        type=int,
        default=None,
        help="Monitor index to open window on (use --list-monitors to see available monitors)",
    )
    parser.add_argument("--list-monitors", action="store_true", help="List available monitors and exit")
    parser.add_argument(
        "--log-level",
        type=str,
        default="DEBUG",
        choices=["FATAL", "ERROR", "WARNING", "INFO", "DEBUG", "TRACE"],
        help="Logging level",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="Log file path (auto-generated if not specified)",
    )

    args = parser.parse_args()

    # Configure logging
    configure_logging(
        level=args.log_level,
        log_to_file=args.log_file is not None,
        log_file_path=args.log_file
    )

    info("Starting Oblique")
    debug(f"Arguments: {vars(args)}")

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
            debug(f"Audio channels: {audio_channels}")
        except ValueError:
            error("Audio-channels must be comma-separated integers (e.g., '0,1')")
            return

    if args.audio_device is not None:
        debug(f"Using audio device ID: {args.audio_device}")
        audio_input = AudioDeviceInput(device_id=args.audio_device, channels=audio_channels)
    elif args.audio_file:
        debug(f"Using audio file: {args.audio_file}")
        audio_input = AudioFileInput(file_path=args.audio_file)
    else:
        error("No audio input specified")
        return

    # Create the patch
    if isinstance(audio_input, AudioDeviceInput) and audio_input.device_name.lower() == "syntakt":
        patch = create_demo_syntakt(args.width, args.height, audio_input)
    else:
        patch = audio_file_demo_patch(args.width, args.height)

    # patch = audio_file_demo_patch(args.width, args.height)


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
        info("Shutting down...")
    except Exception as e:
        error(f"Engine error: {e}")
        raise


if __name__ == "__main__":
    main()
