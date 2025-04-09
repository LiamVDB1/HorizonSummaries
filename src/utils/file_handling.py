# src/utils/file_handling.py
"""
Utility functions for file handling operations.
"""

import os
import json
import re # Import the regular expression module
from pathlib import Path
from typing import Union, Dict, List, Any
import logging

logger = logging.getLogger("horizon_summaries") # Assuming logger is configured elsewhere


def ensure_directory(directory_path: Union[str, Path]) -> str:
    """
    Ensure that a directory exists, creating it if it doesn't.

    Args:
        directory_path (Union[str, Path]): Path to the directory

    Returns:
        str: The absolute path to the directory as a string
    """
    # Convert Path object to string if necessary, and resolve to absolute path
    dir_path = Path(directory_path).resolve()
    dir_path.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Ensured directory exists: {str(dir_path)}")
    return str(dir_path)


def save_to_file(content: str, file_path: Union[str, Path]) -> str:
    """
    Save content to a file, creating the directory if it doesn't exist.

    Args:
        content (str): Content to save
        file_path (Union[str, Path]): Path to save the file

    Returns:
        str: The absolute path to the saved file as a string
    """
    abs_file_path = Path(file_path).resolve()
    # Ensure directory exists using the function above
    ensure_directory(abs_file_path.parent)

    # Write content to file
    try:
        with open(abs_file_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.debug(f"Content saved to file: {str(abs_file_path)}")
        return str(abs_file_path)
    except IOError as e:
        logger.error(f"Failed to write to file {abs_file_path}: {e}", exc_info=True)
        raise


def read_file(file_path: Union[str, Path]) -> str:
    """
    Read content from a file.

    Args:
        file_path (Union[str, Path]): Path to the file

    Returns:
        str: The content of the file
    """
    abs_file_path = Path(file_path).resolve()
    if not abs_file_path.is_file():
        logger.error(f"File not found: {str(abs_file_path)}")
        raise FileNotFoundError(f"File not found: {str(abs_file_path)}")

    try:
        with open(abs_file_path, "r", encoding="utf-8") as f:
            content = f.read()
        logger.debug(f"Content read from file: {str(abs_file_path)}")
        return content
    except IOError as e:
        logger.error(f"Failed to read file {abs_file_path}: {e}", exc_info=True)
        raise


def read_json(file_path: Union[str, Path]) -> Union[Dict, List]:
    """
    Read JSON data from a file.

    Args:
        file_path (Union[str, Path]): Path to the JSON file

    Returns:
        Union[Dict, List]: The data from the JSON file
    """
    content = read_file(file_path) # Use read_file to handle path resolution and errors
    try:
        data = json.loads(content)
        logger.debug(f"JSON data read from file: {str(Path(file_path).resolve())}")
        return data
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON from file {Path(file_path).resolve()}: {e}", exc_info=True)
        raise ValueError(f"Invalid JSON format in file: {file_path}") from e


def save_json(data: Union[Dict, List, Any], file_path: Union[str, Path]) -> str:
    """
    Save data to a JSON file.

    Args:
        data (Union[Dict, List, Any]): Data to save
        file_path (Union[str, Path]): Path to save the file

    Returns:
        str: The path to the saved file as a string
    """
    abs_file_path = Path(file_path).resolve()
    # Ensure directory exists
    ensure_directory(abs_file_path.parent)

    # Write data to JSON file
    try:
        with open(abs_file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.debug(f"JSON data saved to file: {str(abs_file_path)}")
        return str(abs_file_path)
    except (IOError, TypeError) as e:
        logger.error(f"Failed to save JSON to file {abs_file_path}: {e}", exc_info=True)
        raise


def get_file_extension(file_path: Union[str, Path]) -> str:
    """
    Get the lowercased extension of a file (including the dot).

    Args:
        file_path (Union[str, Path]): Path to the file

    Returns:
        str: The extension of the file (e.g., '.txt', '.mp3'). Returns empty string if no extension.
    """
    return Path(file_path).suffix.lower()


def sanitize_filename(filename: str, replacement: str = "_") -> str:
    """
    Removes or replaces characters that are invalid in filenames across common OS.

    Args:
        filename (str): The original filename or string to sanitize.
        replacement (str): The character to use for replacing invalid characters. Defaults to '_'.

    Returns:
        str: The sanitized filename. Returns a default name if the result is empty.
    """
    if not filename:
        return "sanitized_filename" # Handle empty input

    # Characters invalid in Windows filenames (most restrictive set)
    # Includes control characters 0-31, and <>:"/\|?*
    # We also replace sequences of dots or spaces often problematic.
    # Remove control characters
    sanitized = "".join(c for c in filename if ord(c) >= 32)

    # Replace invalid characters with the replacement string
    sanitized = re.sub(r'[<>:"/\\|?*]', replacement, sanitized)

    # Replace sequences of dots or spaces, and leading/trailing dots/spaces
    sanitized = re.sub(r'\.+', '.', sanitized) # Collapse multiple dots
    sanitized = re.sub(r'\s+', replacement, sanitized) # Replace whitespace sequences
    sanitized = sanitized.strip('. ') # Remove leading/trailing dots/spaces

    # Ensure filename is not empty after sanitization
    if not sanitized:
        sanitized = "sanitized_filename"

    # Optional: Limit filename length (e.g., for older systems)
    # max_len = 250
    # if len(sanitized) > max_len:
    #     name, ext = os.path.splitext(sanitized)
    #     sanitized = name[:max_len - len(ext)] + ext
    #     logger.warning(f"Sanitized filename truncated: {sanitized}")

    logger.debug(f"Sanitized '{filename}' to '{sanitized}'")
    return sanitized

