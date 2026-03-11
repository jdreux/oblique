import sys
import types
from pathlib import Path

from tests.utils.stubs import load_module, setup_stubs


ROOT = Path(__file__).resolve().parents[2]


def _ensure_fft_bands_stub() -> None:
    processing_pkg = sys.modules.get("processing")
    if processing_pkg is None or not hasattr(processing_pkg, "__path__"):
        processing_pkg = types.ModuleType("processing")
        processing_pkg.__path__ = [str(ROOT / "processing")]
        sys.modules["processing"] = processing_pkg

    if "processing.fft_bands" not in sys.modules:
        fft_bands_mod = types.ModuleType("processing.fft_bands")

        class FFTBands:
            pass

        fft_bands_mod.FFTBands = FFTBands
        sys.modules["processing.fft_bands"] = fft_bands_mod


def test_circle_echo_resolves_callable_params():
    setup_stubs()
    _ensure_fft_bands_stub()
    module = load_module(
        "modules.audio_reactive.circle_echo",
        ROOT / "modules/audio_reactive/circle_echo.py",
    )

    calls: dict[str, int] = {"width": 0, "height": 0, "n_circles": 0, "mod_depth": 0, "audio_level": 0}

    def _mark(name: str, value: int | float):
        def _resolver() -> int | float:
            calls[name] += 1
            return value

        return _resolver

    params = module.CircleEchoParams(
        width=_mark("width", 640),
        height=_mark("height", 360),
        n_circles=_mark("n_circles", 12),
        mod_depth=_mark("mod_depth", 0.75),
        audio_level=_mark("audio_level", 0.25),
    )

    class DummyBands:
        def process(self) -> list[float]:
            return [0.1, 0.2, 0.3]

    circle_echo = module.CircleEcho(params, DummyBands())
    uniforms = circle_echo.prepare_uniforms(0.0)

    assert uniforms["u_resolution"] == (640, 360)
    assert uniforms["u_n_circles"] == 12
    assert uniforms["u_mod_depth"] == 0.75
    assert uniforms["u_audio_level"] == 0.25
    assert uniforms["u_band_amps"] == (0.1, 0.2, 0.3)
    assert calls == {"width": 1, "height": 1, "n_circles": 1, "mod_depth": 1, "audio_level": 1}


def test_spectral_visualizer_resolves_callable_params():
    setup_stubs()
    _ensure_fft_bands_stub()
    module = load_module(
        "modules.audio_reactive.spectral_visualizer",
        ROOT / "modules/audio_reactive/spectral_visualizer.py",
    )

    calls: dict[str, int] = {"width": 0, "height": 0, "num_bands": 0}

    def _mark(name: str, value: int):
        def _resolver() -> int:
            calls[name] += 1
            return value

        return _resolver

    params = module.SpectralVisualizerParams(
        width=_mark("width", 320),
        height=_mark("height", 200),
        num_bands=_mark("num_bands", 64),
    )

    class DummyBands:
        def process(self) -> list[float]:
            return [0.4, 0.2]

    visualizer = module.SpectralVisualizerModule(
        params=params,
        band_levels_processor=DummyBands(),
    )
    uniforms = visualizer.prepare_uniforms(1.0)

    assert uniforms["u_resolution"] == (320, 200)
    assert uniforms["u_num_bands"] == 64
    assert uniforms["u_bands"][:2] == [0.4, 0.2]
    assert len(uniforms["u_bands"]) == module.SHADER_BANDS_SIZE
    assert calls == {"width": 1, "height": 1, "num_bands": 1}
