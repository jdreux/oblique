import numpy as np
from typing import Any, Callable, Dict
from processing.base_processing_operator import BaseProcessingOperator

class Envelope(BaseProcessingOperator):
    """
    Generic envelope follower for any 1D input (e.g., amplitude, feature stream).
    Applies exponential smoothing to the input signal.
    """
    metadata: Dict[str, Any] = {
        "name": "Envelope",
        "description": "Generic envelope follower for any 1D input (not just amplitude).",
        "parameters": {"alpha": float}
    }

    def __init__(self, input_fn: Callable[[], float], alpha: float = 0.1):
        super().__init__()
        self.input_fn = input_fn
        self.alpha = alpha
        self.value = 0.0

    def process(self) -> float:
        x = self.input_fn()
        self.value = self.alpha * x + (1 - self.alpha) * self.value
        return self.value

if __name__ == "__main__":
    import numpy as np
    # Example: follow a noisy sine wave
    t = np.linspace(0, 2 * np.pi, 100)
    signal = np.sin(t) + 0.2 * np.random.randn(100)
    idx = [0]
    def input_fn():
        v = signal[idx[0]]
        idx[0] += 1
        return v if idx[0] < len(signal) else 0.0
    env = Envelope(input_fn, alpha=0.2)
    for _ in range(100):
        print(env.process()) 