from typing import Callable, List, Optional

from inputs.audio.core.base_audio_input import BaseAudioInput
from modules.core.base_av_module import BaseAVModule


class ObliquePatch:
    """
    Main user-facing builder for AV chains in Oblique.
    Manages modules, connections, and output selection.
    """

    def __init__(self,
        tick_callback: Callable[[float], BaseAVModule],
        audio_output: Optional[BaseAudioInput] = None,
    ) -> None:
        """
        Initialize an empty patch.
        """
        self.audio_output: Optional[BaseAudioInput] = audio_output
        self.tick_callback: Callable[[float], BaseAVModule] = tick_callback
        self._override_scene: Optional[BaseAVModule] = None

    def tick(self, t: float) -> BaseAVModule:
        """
        Call the tick callback, or return the override scene if set.
        """
        if self._override_scene is not None:
            return self._override_scene
        return self.tick_callback(t)