from typing import Any, List

from inputs.base_input import BaseInput
from modules.base_av_module import BaseAVModule


class ObliquePatch:
    """
    Main user-facing builder for AV chains in Oblique.
    Manages modules, connections, and output selection.
    """

    def __init__(self) -> None:
        """
        Initialize an empty patch.
        """
        self.inputs: List[BaseInput] = []
        self.modules: List[BaseAVModule] = []
        self._graph: List[Any] = []  # Could be refined to a DAG structure

    def input(self, input_module: BaseInput) -> BaseInput:
        """
        Register an input module (e.g., audio, MIDI).
        Returns a handle to the input's output for chaining.
        """
        self.inputs.append(input_module)
        self._graph.append(input_module)
        return input_module

    def add(self, module: BaseAVModule) -> BaseAVModule:
        """
        Add a processing or rendering module to the patch.
        Returns a handle to the module's output for chaining.
        """
        self.modules.append(module)
        self._graph.append(module)
        return module

    def get_output(self) -> BaseAVModule | None:
        """
        Return the final output node (renderer or passthrough).
        If no renderer is present, returns a default DebugModule instance.
        """
        if self.modules:
            return self.modules[-1]
        return None

    def get_audio_input(self) -> BaseInput | None:
        """
        Return the audio input node.
        """
        if len(self.inputs) == 0:
            return None
        return self.inputs[0]

    def get_graph(self) -> List[Any]:
        """
        Return a representation of the patch's module graph (for debugging or introspection).
        """
        return self._graph
