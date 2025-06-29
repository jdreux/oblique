#!/usr/bin/env python3
"""
Oblique - Modular AV Synthesizer
Main entry point for the application.
"""

import sys
import os
import argparse

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.engine import ObliqueEngine
from modules.animated_grid import AnimatedGrid


def main():
    """Main entry point for Oblique."""
    parser = argparse.ArgumentParser(description='Oblique - Audio-Reactive AV Synthesizer')
    parser.add_argument('--audio', '-a', type=str, help='Audio file to play (WAV, FLAC, MP3, etc.)')
    parser.add_argument('--width', '-w', type=int, default=390, help='Window width')
    parser.add_argument('--height', type=int, default=844, help='Window height')
    parser.add_argument('--grid-size', type=float, default=25.0, help='Grid size')
    parser.add_argument('--animation-speed', type=float, default=1.5, help='Animation speed')
    parser.add_argument('--audio-sensitivity', type=float, default=3.0, help='Audio sensitivity')
    
    args = parser.parse_args()
    
    print("🎵 Starting Oblique AV Synthesizer...")
    print("🏗️  Architecture: Input → Processing → Rendering → Output")
    
    try:
        # Create and initialize the engine
        title = "Oblique - Audio-Reactive Grid"
        if args.audio:
            title += f" ({os.path.basename(args.audio)})"
        
        engine = ObliqueEngine(args.width, args.height, title, args.audio)
        engine.initialize()
        
        # Create and add the animated grid module
        module = AnimatedGrid({
            'grid_size': args.grid_size,
            'animation_speed': args.animation_speed,
            'line_width': 0.02,
            'color': (0.8, 0.3, 0.9),
            'audio_sensitivity': args.audio_sensitivity,
            'base_intensity': 0.2
        })
        
        engine.add_module(module)
        
        print("✅ Engine ready! Press ESC or close window to exit.")
        print("📊 Module: Audio-Reactive Animated Grid")
        print("🔄 Signal Flow: Audio → Features → Normalization → Events → Rendering → Composition → Display")
        
        if args.audio:
            print(f"🎵 Audio: {args.audio}")
        else:
            print("🎵 Audio:: No audio file provided")
        
        # Run the main loop
        engine.run()
        
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 