"""
Logging setup and utilities for the application.
"""

import logging
import os
import sys
from datetime import datetime
from typing import Optional, Dict

from src.config import Config

# Using colorlog for colored terminal output
try:
    import colorlog
except ImportError:
    print("Optional 'colorlog' package not found. Install with 'pip install colorlog' for colored console logs.")
    colorlog = None

# Store loggers to prevent duplicates
_loggers: Dict[str, logging.Logger] = {}

def setup_logger(logger_name: str, log_file: Optional[str] = None) -> logging.Logger:
    """
    Set up and configure a logger with colored console output.

    Args:
        logger_name (str): Name of the logger
        log_file (Optional[str], optional): Path to log file. Defaults to Config.LOG_FILE.

    Returns:
        logging.Logger: Configured logger
    """
    # Return existing logger if already configured
    if logger_name in _loggers:
        return _loggers[logger_name]

    # Create logger and set propagate to False to prevent double logging
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.getLevelName(Config.LOG_LEVEL))
    logger.propagate = False

    # Remove existing handlers if any (to prevent duplicate handlers)
    if logger.handlers:
        logger.handlers.clear()

    # Console handler with colors
    if colorlog and sys.stdout.isatty():  # Use colors only if colorlog is available and in a terminal
        # Color mapping
        color_formatter = colorlog.ColoredFormatter(
            "%(log_color)s[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s%(reset)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            },
            secondary_log_colors={},
            style='%'
        )
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(color_formatter)
    else:
        # Standard formatter without colors
        standard_formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(standard_formatter)

    logger.addHandler(console_handler)

    # File handler if specified
    if log_file or Config.LOG_FILE:
        log_file = log_file or Config.LOG_FILE

        # Ensure log directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        # Plain formatter for file (no colors in files)
        file_formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    # Store in dict to prevent recreating
    _loggers[logger_name] = logger
    return logger


def clear_loggers():
    """
    Clear all configured loggers.
    Useful for testing or when reloading configuration.
    """
    for logger_name, logger in _loggers.items():
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
    _loggers.clear()