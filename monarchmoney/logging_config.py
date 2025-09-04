"""
Logging configuration for MonarchMoney Enhanced.

Provides structured logging with configurable levels and outputs.
"""

import logging
import logging.config
import os
from typing import Optional


class MonarchLogger:
    """Wrapper for structured logging in MonarchMoney."""

    def __init__(self, name: str, level: Optional[str] = None):
        self.logger = logging.getLogger(name)

        # Set level from environment or default to INFO
        log_level = level or os.getenv("MONARCHMONEY_LOG_LEVEL", "INFO")
        self.logger.setLevel(getattr(logging, log_level.upper()))

        # Avoid duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()

    def _setup_handlers(self):
        """Setup console and file handlers."""
        # Console handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.INFO)

        # File handler (optional, only if log directory exists)
        log_dir = os.getenv("MONARCHMONEY_LOG_DIR", ".")
        if os.path.exists(log_dir) and os.access(log_dir, os.W_OK):
            file_handler = logging.FileHandler(
                os.path.join(log_dir, "monarchmoney.log")
            )
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
            )
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(logging.DEBUG)
            self.logger.addHandler(file_handler)

        self.logger.addHandler(console_handler)

    def debug(self, message: str, **kwargs):
        """Log debug message with optional structured data."""
        if kwargs:
            self.logger.debug(f"{message} - {kwargs}")
        else:
            self.logger.debug(message)

    def info(self, message: str, **kwargs):
        """Log info message with optional structured data."""
        if kwargs:
            self.logger.info(f"{message} - {kwargs}")
        else:
            self.logger.info(message)

    def warning(self, message: str, **kwargs):
        """Log warning message with optional structured data."""
        if kwargs:
            self.logger.warning(f"{message} - {kwargs}")
        else:
            self.logger.warning(message)

    def error(self, message: str, exc_info: Optional[Exception] = None, **kwargs):
        """Log error message with optional exception info and structured data."""
        extra_info = f" - {kwargs}" if kwargs else ""
        self.logger.error(f"{message}{extra_info}", exc_info=exc_info)

    def critical(self, message: str, **kwargs):
        """Log critical message with optional structured data."""
        if kwargs:
            self.logger.critical(f"{message} - {kwargs}")
        else:
            self.logger.critical(message)


def setup_logging(level: str = "INFO") -> MonarchLogger:
    """
    Setup logging for the MonarchMoney package.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        MonarchLogger instance
    """
    return MonarchLogger("monarchmoney", level)


# Global logger instance
logger = setup_logging()
