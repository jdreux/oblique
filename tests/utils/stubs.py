import sys
import sys
import types
import importlib.util
from pathlib import Path


def load_module(name: str, path: Path):
    """Load a module from *path* and register it under *name* in ``sys.modules``."""
    parts = name.split(".")
    for i in range(1, len(parts)):
        pkg_name = ".".join(parts[:i])
        pkg_path = path.parents[len(parts) - i - 1]
        if pkg_name not in sys.modules:
            pkg = types.ModuleType(pkg_name)
            pkg.__path__ = [str(pkg_path)]
            sys.modules[pkg_name] = pkg
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    sys.modules[name] = module
    return module


def setup_stubs() -> None:
    """Install stub modules for external dependencies."""
    root = Path(__file__).resolve().parents[1].parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    if "glfw" not in sys.modules:
        sys.modules["glfw"] = types.SimpleNamespace(
            CONTEXT_VERSION_MAJOR=3,
            CONTEXT_VERSION_MINOR=3,
            OPENGL_PROFILE=0,
            OPENGL_CORE_PROFILE=0,
            _GLFWwindow=object,
            init=lambda: True,
            window_hint=lambda *a, **k: None,
            create_window=lambda *a, **k: object(),
            make_context_current=lambda *a, **k: None,
            window_should_close=lambda win: True,
            terminate=lambda: None,
            get_monitors=lambda: [],
            get_monitor_name=lambda m: "Monitor",
            get_video_mode=lambda m: types.SimpleNamespace(size=(800, 600), refresh_rate=60),
            get_monitor_pos=lambda m: (0, 0),
            get_monitor_workarea=lambda m: (0, 0, 800, 600),
            set_window_pos=lambda *a, **k: None,
            poll_events=lambda: None,
            swap_buffers=lambda win: None,
        )

    class DummyTexture:
        def __init__(self):
            self.filter = None
            self.repeat_x = False
            self.repeat_y = False

        def use(self, location: int = 0) -> None:
            pass

    class DummyProgram(dict):
        def release(self) -> None:
            pass

    class DummyBuffer:
        def release(self) -> None:
            pass

    class DummyVAO:
        def release(self) -> None:
            pass

        def render(self, *args) -> None:
            pass

    class DummyFramebuffer:
        def use(self) -> None:
            pass

        def release(self) -> None:
            pass

    class DummyContext:
        screen = types.SimpleNamespace(size=(1, 1))

        def program(self, vertex_shader: str, fragment_shader: str) -> DummyProgram:
            return DummyProgram()

        def buffer(self, data: bytes) -> DummyBuffer:
            return DummyBuffer()

        def simple_vertex_array(self, program: DummyProgram, vbo: DummyBuffer, *attrs) -> DummyVAO:
            return DummyVAO()

        def texture(self, size, components, dtype, alignment):
            return DummyTexture()

        def framebuffer(self, color_attachments):
            return DummyFramebuffer()

        def clear(self, *args):
            pass

        viewport = (0, 0, 0, 0)

    if "moderngl" not in sys.modules:
        sys.modules["moderngl"] = types.SimpleNamespace(
            Texture=DummyTexture,
            Program=DummyProgram,
            Buffer=DummyBuffer,
            VertexArray=DummyVAO,
            Context=DummyContext,
            create_context=lambda: DummyContext(),
            NEAREST=0,
            LINEAR=1,
            TRIANGLE_STRIP=0,
        )

    class DummyOutputStream:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            pass

        def write(self, chunk):
            pass

    if "sounddevice" not in sys.modules:
        sys.modules["sounddevice"] = types.SimpleNamespace(OutputStream=DummyOutputStream)

    if "abletonlink" not in sys.modules:
        sys.modules["abletonlink"] = types.SimpleNamespace(Link=lambda bpm: None)

    # Ensure core package and basic logger stubs
    if "core" not in sys.modules:
        core_pkg = types.ModuleType("core")
        core_pkg.__path__ = [str(root / "core")]
        sys.modules["core"] = core_pkg
    if "core.logger" not in sys.modules:
        logger_stub = types.ModuleType("core.logger")
        logger_stub.error = lambda *a, **k: None
        logger_stub.warning = lambda *a, **k: None
        logger_stub.info = lambda *a, **k: None
        logger_stub.debug = lambda *a, **k: None
        sys.modules["core.logger"] = logger_stub

    if "core.renderer" not in sys.modules:
        load_module("core.renderer", root / "core" / "renderer.py")

    if "inputs.audio.core.base_input" not in sys.modules:
        base_mod = types.ModuleType("inputs.audio.core.base_input")

        class DummyBaseInput:
            sample_rate = 48000
            num_channels = 2
            device_name = "dummy"

            def __init__(self, chunk_size: int = 1) -> None:
                self.chunk_size = chunk_size

            def start(self) -> None:  # pragma: no cover - stub method
                pass

            def stop(self) -> None:  # pragma: no cover - stub method
                pass

            def read(self, channels=None):  # pragma: no cover - stub method
                return None

            def peek(self, n_buffers: int = 1, channels=None):  # pragma: no cover - stub method
                return None

        base_mod.BaseInput = DummyBaseInput

        inputs_pkg = types.ModuleType("inputs")
        inputs_pkg.__path__ = []
        sys.modules.setdefault("inputs", inputs_pkg)
        audio_pkg = types.ModuleType("inputs.audio")
        audio_pkg.__path__ = []
        sys.modules.setdefault("inputs.audio", audio_pkg)
        audio_core_pkg = types.ModuleType("inputs.audio.core")
        audio_core_pkg.__path__ = []
        sys.modules.setdefault("inputs.audio.core", audio_core_pkg)
        sys.modules["inputs.audio.core.base_input"] = base_mod

    # Stub modules package to avoid heavy imports
    if "modules" not in sys.modules:
        modules_pkg = types.ModuleType("modules")
        modules_pkg.__path__ = [str(root / "modules")]
        sys.modules["modules"] = modules_pkg
    if "modules.core" not in sys.modules:
        modules_core_pkg = types.ModuleType("modules.core")
        modules_core_pkg.__path__ = [str(root / "modules" / "core")]
        sys.modules["modules.core"] = modules_core_pkg
    if "modules.core.base_av_module" not in sys.modules:
        load_module("modules.core.base_av_module", root / "modules" / "core" / "base_av_module.py")
