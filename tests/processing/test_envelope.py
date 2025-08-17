from pathlib import Path

import numpy as np

from tests.utils.stubs import setup_stubs, load_module

ROOT = Path(__file__).resolve().parents[2]


def test_envelope_smoothing() -> None:
    setup_stubs()
    mod = load_module("processing.envelope", ROOT / "processing" / "envelope.py")

    values = [1.0, 0.0]

    def input_fn() -> float:
        return values.pop(0) if values else 0.0

    env = mod.Envelope(input_fn, decay=0.5)
    assert np.isclose(env.process(), 0.5)
    assert np.isclose(env.process(), 0.25)
