"""
Utility functions for file handling operations.
"""

import os
import json
from pathlib import Path
from typing import Union, Dict, List, Any
import logging

logger = logging.getLogger("horizon_summaries")


def ensure_directory(directory_path: str) -> str:
    """
    Ensure that a directory exists, creating it if it doesn't.

    Args:
        directory_path (str): Path to the directory

    Returns:
        str: The path to the directory
    """
    os.makedirs(directory_path, exist_ok=True)
    return directory_path


def save_to_file(content: str, file_path: str) -> str:
    """
    Save content to a file, creating the directory if it doesn't exist.

    Args:
        content (str): Content to save
        file_path (str): Path to save the file

    Returns:
        str: The path to the saved file
    """
    # Ensure directory exists
    directory = os.path.dirname(file_path)
    ensure_directory(directory)

    # Write content to file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    return file_path


def read_file(file_path: str) -> str:
    """
    Read content from a file.

    Args:
        file_path (str): Path to the file

    Returns:
        str: The content of the file
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def read_json(file_path: str) -> Union[Dict, List]:
    """
    Read JSON data from a file.

    Args:
        file_path (str): Path to the JSON file

    Returns:
        Union[Dict, List]: The data from the JSON file
    """
    if not os.path.exists(file_path):
        logger.error(f"JSON file not found: {file_path}")
        raise FileNotFoundError(f"JSON file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: Union[Dict, List], file_path: str) -> str:
    """
    Save data to a JSON file.

    Args:
        data (Union[Dict, List]): Data to save
        file_path (str): Path to save the file

    Returns:
        str: The path to the saved file
    """
    # Ensure directory exists
    directory = os.path.dirname(file_path)
    ensure_directory(directory)

    # Write data to JSON file
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return file_path


def get_file_extension(file_path: str) -> str:
    """
    Get the extension of a file.

    Args:
        file_path (str): Path to the file

    Returns:
        str: The extension of the file
    """
    return os.path.splitext(file_path)[1].lower()