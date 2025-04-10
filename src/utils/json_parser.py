"""
Utilities for parsing and extracting JSON from LLM outputs.
"""

import json
import re
from typing import Any, Optional, Dict, List, Union
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def parse_json_from_llm(
        llm_output: str,
        description: str = "LLM response",
        max_attempts: int = 3
) -> Optional[Any]:
    """
    Attempts to parse a JSON object potentially embedded in LLM text output.
    Handles common issues like markdown code fences, extra text, and syntax errors.

    Args:
        llm_output (str): The raw text output from the LLM.
        description (str): A description for logging purposes (e.g., "term analysis").
        max_attempts (int): Maximum number of parsing strategies to attempt.

    Returns:
        Optional[Any]: The parsed JSON object (dict, list, etc.) or None if parsing fails.
    """
    if not llm_output or not llm_output.strip():
        logger.warning(f"Empty or whitespace-only input for {description} JSON parsing")
        return None

    logger.debug(f"Attempting to parse JSON from {description}: {llm_output[:200]}...")

    # Clean common markdown fences
    cleaned_output = llm_output.strip()

    # 1. Direct parsing attempt (fastest path)
    try:
        parsed_json = json.loads(cleaned_output)
        logger.debug(f"Successfully parsed JSON for {description} on first attempt.")
        return parsed_json
    except json.JSONDecodeError:
        # Continue to more sophisticated cleaning and parsing
        pass

    # 2. Remove markdown code blocks if present
    if cleaned_output.startswith("```"):
        # Handle ```json or just ```
        if cleaned_output.startswith("```json"):
            cleaned_output = cleaned_output[7:]
        else:
            cleaned_output = cleaned_output[3:]

        # Remove closing code fence
        if cleaned_output.endswith("```"):
            cleaned_output = cleaned_output[:-3]

        cleaned_output = cleaned_output.strip()

        # Try parsing again after removing code fences
        try:
            parsed_json = json.loads(cleaned_output)
            logger.debug(f"Successfully parsed JSON for {description} after removing code fences.")
            return parsed_json
        except json.JSONDecodeError:
            # Continue to next strategy
            pass

    # 3. Try to find JSON object within the text using regex patterns
    # Look for object patterns first
    try:
        object_match = re.search(r'({[\s\S]*?})', cleaned_output)
        if object_match:
            potential_json = object_match.group(1)
            parsed_json = json.loads(potential_json)
            logger.warning(f"Successfully parsed JSON object for {description} using regex extraction.")
            return parsed_json

        # Look for array patterns
        array_match = re.search(r'(\[[\s\S]*?\])', cleaned_output)
        if array_match:
            potential_json = array_match.group(1)
            parsed_json = json.loads(potential_json)
            logger.warning(f"Successfully parsed JSON array for {description} using regex extraction.")
            return parsed_json
    except json.JSONDecodeError:
        # Continue to next strategy
        pass

    # 4. Last resort: Try to find the outermost matching braces/brackets
    try:
        # Try object
        start = cleaned_output.find('{')
        end = cleaned_output.rfind('}')
        if start != -1 and end != -1 and start < end:
            potential_json = cleaned_output[start:end + 1]
            parsed_json = json.loads(potential_json)
            logger.warning(f"Successfully parsed JSON for {description} by finding outer braces.")
            return parsed_json

        # Try array
        start = cleaned_output.find('[')
        end = cleaned_output.rfind(']')
        if start != -1 and end != -1 and start < end:
            potential_json = cleaned_output[start:end + 1]
            parsed_json = json.loads(potential_json)
            logger.warning(f"Successfully parsed JSON array for {description} by finding outer brackets.")
            return parsed_json
    except json.JSONDecodeError as e:
        logger.error(f"Final JSON parsing attempt failed for {description}: {e}.")
        logger.debug(f"Problematic content (first 200 chars): {cleaned_output[:200]}...")
        return None

    logger.error(f"All JSON parsing attempts failed for {description}.")
    return None


def parse_structured_json(
        llm_output: str,
        expected_keys: List[str] = None,
        description: str = "structured data"
) -> Optional[Dict[str, Any]]:
    """
    Parses JSON with expected structure and validates required keys are present.

    Args:
        llm_output (str): Raw LLM output containing JSON.
        expected_keys (List[str]): List of expected top-level keys that must be present.
        description (str): Description for logging purposes.

    Returns:
        Optional[Dict[str, Any]]: Parsed JSON dict if valid, None otherwise.
    """
    data = parse_json_from_llm(llm_output, description)

    if not data:
        return None

    if not isinstance(data, dict):
        logger.error(f"Expected dictionary for {description}, but got {type(data).__name__}")
        return None

    if expected_keys:
        missing_keys = [key for key in expected_keys if key not in data]
        if missing_keys:
            logger.error(f"Missing required keys in {description}: {', '.join(missing_keys)}")
            return None

    return data


def extract_json_list(
        llm_output: str,
        description: str = "list data",
        min_items: int = 0,
        item_type: type = None
) -> Optional[List[Any]]:
    """
    Extracts and validates a JSON list from LLM output.

    Args:
        llm_output (str): Raw LLM output containing JSON.
        description (str): Description for logging purposes.
        min_items (int): Minimum number of items expected.
        item_type (type): Expected type of items (str, dict, etc.)

    Returns:
        Optional[List[Any]]: Parsed JSON list if valid, None otherwise.
    """
    data = parse_json_from_llm(llm_output, description)

    if not data:
        return None

    if not isinstance(data, list):
        logger.error(f"Expected list for {description}, but got {type(data).__name__}")
        return None

    if min_items > 0 and len(data) < min_items:
        logger.warning(f"Expected at least {min_items} items in {description}, but got {len(data)}")
        # Still return the list even if fewer items than expected

    if item_type and not all(isinstance(item, item_type) for item in data):
        logger.warning(f"Not all items in {description} are of expected type {item_type.__name__}")
        # Convert items to expected type if possible
        try:
            return [item_type(item) for item in data]
        except (ValueError, TypeError):
            logger.error(f"Could not convert all items to {item_type.__name__}")
            # Return the original list

    return data