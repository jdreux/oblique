"""Demonstrate the transport clock with Link or MIDI synchronization."""

import argparse
import time

from inputs.transport import AbletonLinkClock, MidiClock, TransportClock


def main() -> None:
    parser = argparse.ArgumentParser(description="Transport clock demo")
    parser.add_argument("--link", action="store_true", help="Sync via Ableton Link")
    parser.add_argument("--midi", metavar="PORT", help="Sync to a MIDI clock input")
    args = parser.parse_args()

    if args.midi:
        clock = MidiClock(port=args.midi)
    elif args.link:
        clock = AbletonLinkClock()
    else:
        clock = TransportClock()

    print("Press Ctrl+C to stop")
    try:
        while True:
            state = clock.state()
            print(
                f"BPM {state.bpm:.1f} | Bar {state.bar} Beat {state.beat} "
                f"Phase {state.phase:.2f}",
                end="\r",
            )
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
