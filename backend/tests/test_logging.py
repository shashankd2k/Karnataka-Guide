"""
Unit tests for structured logging setup.
"""

from app.core.logging import get_logger, setup_logging


def test_setup_logging_console_mode():
    """Verify logging initializes in console mode."""
    setup_logging(log_level="DEBUG", log_json=False)
    logger = get_logger("test.console")
    logger.info("test_console_log", message="Console log test successful")


def test_setup_logging_json_mode():
    """Verify logging initializes in JSON mode."""
    setup_logging(log_level="INFO", log_json=True)
    logger = get_logger("test.json")
    logger.info("test_json_log", message="JSON log test successful", key="value")
