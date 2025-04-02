"""
Logging setup and utilities for the application.
"""

import logging
import os
import sys
from datetime import datetime
from typing import Optional

from src.config import Config


def setup_logger(logger_name: str, log_file: Optional[str] = None) -> logging.Logger:
    """
    Set up and configure a logger.

    Args:
        logger_name (str): Name of the logger
        log_file (Optional[str], optional): Path to log file. Defaults to Config.LOG_FILE.

    Returns:
        logging.Logger: Configured logger
    """
    # Create logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.getLevelName(Config.LOG_LEVEL))

    # Create formatter
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Create file handler if specified
    if log_file or Config.LOG_FILE:
        log_file = log_file or Config.LOG_FILE

        # Ensure log directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger