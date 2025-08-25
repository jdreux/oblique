

from core.oblique_patch import ObliquePatch
from modules.core.base_av_module import BaseAVModule
from inputs.midi.core.midi_input import MidiInput
from modules.utilities.debug import DebugModule, DebugParams


def oblique_patch(width: int, height: int) -> ObliquePatch:

    midi_input = MidiInput(
        port_name='IAC Driver Bus 1'
    )

    midi_input.start()

    debug_module = DebugModule(
        DebugParams(
            width=width,
            height=height,
        )
    )

    def _tick_callback(t: float) -> BaseAVModule:
        return debug_module

    return ObliquePatch(
        tick_callback=_tick_callback,
    )