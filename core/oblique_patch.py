from typing import Callable, List, Optional

from inputs.base_input import BaseInput
from modules.core.base_av_module import BaseAVModule


class ObliquePatch:
    """
    Main user-facing builder for AV chains in Oblique.
    Manages modules, connections, and output selection.
    """

    def __init__(self,
        tick_callback: Callable[[float], BaseAVModule],
        audio_output: Optional[BaseInput] = None,
    ) -> None:
        """
        Initialize an empty patch.
        """
        self.audio_output: Optional[BaseInput] = audio_output
        self.tick_callback: Callable[[float], BaseAVModule] = tick_callback

    # def set_inputs(self, inputs: List[BaseInput]) -> None:
    #     """
    #     Register an input module (e.g., audio, MIDI).
    #     Returns a handle to the input's output for chaining.
    #     """
    #     self.inputs = inputs

    # def set_tick_callback(self, callback: Callable[[float, int, int, List[BaseInput]], BaseAVModule]) -> None:
    #     """
    #     Register a callback to be called on each tick (every frame).
    #     """
    #     self.tick_callback = callback

    def tick(self, t: float) -> BaseAVModule:
        """
        Call the tick callback.
        """
        return self.tick_callback(t)

    # def add(self, module: BaseAVModule) -> BaseAVModule:
    #     """
    #     Add a processing or rendering module to the patch.
    #     Returns a handle to the module's output for chaining.
    #     """
    #     self.modules.append(module)
    #     self._graph.append(module)
    #     return module

    # def get_output(self) -> BaseAVModule | None:
    #     """
    #     Return the final output node (renderer or passthrough).
    #     If no renderer is present, returns a default DebugModule instance.
    #     """
    #     if self.modules:
    #         return self.modules[-1]
    #     return None

    # def get_audio_input(self) -> BaseInput | None:
    #     """
    #     Return the audio input node.
    #     """
    #     if len(self.inputs) == 0:
    #         return None
    #     return self.inputs[0]
