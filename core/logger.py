"""
Oblique Logging System

Provides a centralized logging system for the Oblique AV synthesizer.
Supports different log levels, configurable output, and structured logging.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class ObliqueLogger:
    """
    Centralized logging system for Oblique.
    Provides structured logging with different levels:
    - FATAL: Critical errors that prevent operation
    - ERROR: Errors that affect functionality but don't stop execution
    - WARNING: Issues that should be addressed but don't break functionality
    - INFO: General information about system state
    - DEBUG: Detailed information for debugging
    - TRACE: Very detailed information for deep debugging
    """

    _instance: Optional['ObliqueLogger'] = None
    _initialized: bool = False

    def __new__(cls) -> 'ObliqueLogger':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        self._initialized = True
        self._logger: Optional[logging.Logger] = None
        self._log_file: Optional[Path] = None
        self._log_level: int = logging.INFO
        self._console_handler: Optional[logging.StreamHandler] = None
        self._file_handler: Optional[logging.FileHandler] = None

    def configure(
        self,
        level: str = "INFO",
        log_to_file: bool = True,
        log_file_path: Optional[str] = None,
        log_to_console: bool = True,
        format_string: Optional[str] = None
    ) -> None:
        """
        Configure the logging system.
        Args:
            level: Log level ('FATAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'TRACE')
            log_to_file: Whether to log to a file
            log_file_path: Path to log file (auto-generated if None)
            log_to_console: Whether to log to console
            format_string: Custom format string for log messages
        """
        # Create logger
        self._logger = logging.getLogger('oblique')
        self._logger.setLevel(logging.DEBUG)  # Set to lowest level, handlers will filter

        # Clear existing handlers
        self._logger.handlers.clear()

        # Set log level
        level_map = {
            'FATAL': logging.CRITICAL,
            'ERROR': logging.ERROR,
            'WARNING': logging.WARNING,
            'INFO': logging.INFO,
            'DEBUG': logging.DEBUG,
            'TRACE': logging.DEBUG  # TRACE maps to DEBUG in standard logging
        }
        self._log_level = level_map.get(level.upper(), logging.INFO)

        # Default format string
        if format_string is None:
            format_string = '%(asctime)s [%(levelname)s] %(message)s'

        formatter = logging.Formatter(format_string)

        # Console handler
        if log_to_console:
            self._console_handler = logging.StreamHandler(sys.stdout)
            self._console_handler.setLevel(self._log_level)
            self._console_handler.setFormatter(formatter)
            self._logger.addHandler(self._console_handler)

        # File handler
        if log_to_file:
            if log_file_path is None:
                # Create logs directory if it doesn't exist
                logs_dir = Path("logs")
                logs_dir.mkdir(exist_ok=True)

                # Generate log file name with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_file_path = logs_dir / f"oblique_{timestamp}.log"

            self._log_file = Path(log_file_path)
            self._log_file.parent.mkdir(parents=True, exist_ok=True)

            self._file_handler = logging.FileHandler(self._log_file)
            self._file_handler.setLevel(logging.DEBUG)  # File gets all logs
            self._file_handler.setFormatter(formatter)
            self._logger.addHandler(self._file_handler)

            # Log the configuration
            self.info(f"Logging to file: {self._log_file}")

    def get_logger(self) -> logging.Logger:
        """Get the configured logger instance."""
        if self._logger is None:
            self.configure()  # Use default configuration
        return self._logger

    def fatal(self, message: str, **kwargs: Any) -> None:
        """Log a fatal error message."""
        self._log(logging.CRITICAL, message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log an error message."""
        self._log(logging.ERROR, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log a warning message."""
        self._log(logging.WARNING, message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log an info message."""
        self._log(logging.INFO, message, **kwargs)

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log a debug message."""
        self._log(logging.DEBUG, message, **kwargs)

    def _log(self, level: int, message: str, **kwargs: Any) -> None:
        """Internal logging method."""
        if self._logger is None:
            self.configure()

        # Format message with kwargs if provided
        if kwargs:
            formatted_message = message.format(**kwargs)
        else:
            formatted_message = message

        self._logger.log(level, formatted_message)

# Global logger instance
logger = ObliqueLogger()


def get_logger() -> logging.Logger:
    """Get the global logger instance."""
    return logger.get_logger()


def configure_logging(
    level: str = "INFO",
    log_to_file: bool = True,
    log_file_path: Optional[str] = None,
    log_to_console: bool = True
) -> None:
    """Configure the global logging system."""
    logger.configure(
        level=level,
        log_to_file=log_to_file,
        log_file_path=log_file_path,
        log_to_console=log_to_console
    )


# Convenience functions for direct logging
def fatal(message: str, **kwargs: Any) -> None:
    """Log a fatal error message."""
    logger.fatal(message, **kwargs)


def error(message: str, **kwargs: Any) -> None:
    """Log an error message."""
    logger.error(message, **kwargs)


def warning(message: str, **kwargs: Any) -> None:
    """Log a warning message."""
    logger.warning(message, **kwargs)


def info(message: str, **kwargs: Any) -> None:
    """Log an info message."""
    logger.info(message, **kwargs)


def debug(message: str, **kwargs: Any) -> None:
    """Log a debug message."""
    logger.debug(message, **kwargs)


def trace(message: str, **kwargs: Any) -> None:
    """Log a trace message."""
    logger.trace(message, **kwargs)
