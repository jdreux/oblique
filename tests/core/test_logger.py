import importlib.util
import sys
from pathlib import Path


def load_logger_module():
    path = Path(__file__).resolve().parents[2] / "core" / "logger.py"
    spec = importlib.util.spec_from_file_location("core.logger", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["core.logger"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


logger_module = load_logger_module()


def reset_logger():
    """Reset singleton state for isolated testing."""
    logger_module.ObliqueLogger._instance = None
    logger_module.ObliqueLogger._initialized = False


def test_singleton_behavior():
    reset_logger()
    first = logger_module.ObliqueLogger()
    second = logger_module.ObliqueLogger()
    assert first is second


def test_file_logging(tmp_path):
    reset_logger()
    log_file = tmp_path / "test.log"
    logger = logger_module.ObliqueLogger()
    logger.configure(level="INFO", log_to_file=True, log_file_path=str(log_file), log_to_console=False)
    logger.info("hello")
    assert log_file.exists()
    assert "hello" in log_file.read_text()
