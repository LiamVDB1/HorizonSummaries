"""
Utilities for loading and processing Jupiter reference data (terms and names).
"""

import json
import logging
from typing import List, Dict, Any, Optional

from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def load_term_context() -> Dict[str, Any]:
    """
    Loads the complete term context data from jupiter_terms.json.
    Returns the full context data.
    """
    try:
        if Config.JUPITER_TERMS_FILE.exists():
            with open(Config.JUPITER_TERMS_FILE, 'r') as f:
                data = json.load(f)
                logger.info(f"Loaded full term context from {Config.JUPITER_TERMS_FILE}")
                return data
        else:
            logger.warning(f"Known terms file not found: {Config.JUPITER_TERMS_FILE}")
            return {"terms": []}
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from {Config.JUPITER_TERMS_FILE}")
        return {"terms": []}
    except Exception as e:
        logger.error(f"Error loading term context: {e}", exc_info=True)
        return {"terms": []}


def load_people_context() -> Dict[str, Any]:
    """
    Loads the complete name context data from jupiter_names.json.
    Returns the full context data.
    """
    try:
        if Config.JUPITER_PEOPLE_FILE.exists():
            with open(Config.JUPITER_PEOPLE_FILE, 'r') as f:
                data = json.load(f)
                logger.info(f"Loaded full name context from {Config.JUPITER_PEOPLE_FILE}")
                return data
        else:
            logger.warning(f"Known names file not found: {Config.JUPITER_PEOPLE_FILE}")
            return {"people": []}
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from {Config.JUPITER_PEOPLE_FILE}")
        return {"people": []}
    except Exception as e:
        logger.error(f"Error loading name context: {e}", exc_info=True)
        return {"people": []}


def extract_terms_list(term_data: Dict[str, Any]) -> List[str]:
    """
    Extracts a flat list of terms from the rich term context data.
    This is used for compatibility with functions expecting simple term lists.
    """
    terms = []

    if "terms" in term_data and term_data["terms"]:
        for term_obj in term_data["terms"]:
            # Add main term
            if isinstance(term_obj, str):
                terms.append(term_obj)
            elif isinstance(term_obj, dict) and "term" in term_obj:
                terms.append(term_obj["term"])

                # Add acronyms if present
                if "acronyms" in term_obj and term_obj["acronyms"]:
                    terms.extend([a for a in term_obj["acronyms"] if a])

    return [t for t in terms if t]  # Filter out empty strings


def extract_people_list(name_data: Dict[str, Any]) -> List[str]:
    """
    Extracts a flat list of names from the rich name context data.
    This is used for compatibility with functions expecting simple name lists.
    """
    names = []

    if "people" in name_data and name_data["people"]:
        for name_obj in name_data["people"]:
            # Add main name
            if isinstance(name_obj, str):
                names.append(name_obj)
            elif isinstance(name_obj, dict) and "name" in name_obj:
                names.append(name_obj["name"])

                # Add nicknames if present
                if "nicknames" in name_obj and name_obj["nicknames"]:
                    names.extend([n for n in name_obj["nicknames"] if n])

    return [n for n in names if n]  # Filter out empty strings


def format_terms_for_prompt(term_data: Dict[str, Any]) -> str:
    """
    Formats the complete term context data into a rich, LLM-readable format for the prompt.
    """
    if not term_data or "terms" not in term_data or not term_data["terms"]:
        return "No term data available."

    formatted_text = "## Jupiter Terminology Reference\n\n```"

    for term_obj in term_data["terms"]:
        if isinstance(term_obj, str):
            # Simple string format
            formatted_text += f"**{term_obj}**\n\n"
        elif isinstance(term_obj, dict) and "term" in term_obj:
            # Rich object format
            term = term_obj["term"]
            formatted_text += f"### {term}\n"

            # Add acronyms if present
            if "acronyms" in term_obj and term_obj["acronyms"]:
                acronyms = ", ".join(term_obj["acronyms"])
                formatted_text += f"**Acronyms/Alternatives:** {acronyms}\n"

            # Add description if present
            if "description" in term_obj and term_obj["description"]:
                formatted_text += f"**Description:** {term_obj['description']}\n"

            # Add related terms if present
            if "related_terms" in term_obj and term_obj["related_terms"]:
                related = ", ".join(term_obj["related_terms"])
                formatted_text += f"**Related Terms:** {related}\n"

            formatted_text += "\n"

    formatted_text += "```"
    return formatted_text


def format_people_for_prompt(name_data: Dict[str, Any]) -> str:
    """
    Formats the complete name context data into a rich, LLM-readable format for the prompt.
    """
    if not name_data or "people" not in name_data or not name_data["people"]:
        return "No name data available."

    formatted_text = "## Jupiter People Reference\n\n```"

    for name_obj in name_data["people"]:
        if isinstance(name_obj, str):
            # Simple string format
            formatted_text += f"**{name_obj}**\n\n"
        elif isinstance(name_obj, dict) and "name" in name_obj:
            # Rich object format
            name = name_obj["name"]
            formatted_text += f"### {name}\n"

            # Add role if present
            if "role" in name_obj and name_obj["role"]:
                formatted_text += f"**Role:** {name_obj['role']}\n"

            # Add nicknames if present
            if "nicknames" in name_obj and name_obj["nicknames"]:
                nicknames = ", ".join(name_obj["nicknames"])
                formatted_text += f"**Nicknames/Handles:** {nicknames}\n"

            # Add description if present
            if "description" in name_obj and name_obj["description"]:
                formatted_text += f"**Background:** {name_obj['description']}\n"

            formatted_text += "\n"

    formatted_text += "```"
    return formatted_text


def get_known_terms() -> List[str]:
    """
    Gets a simple list of known terms from the reference data.
    """
    term_data = load_term_context()
    terms = extract_terms_list(term_data)
    logger.info(f"Extracted {len(terms)} known Jupiter terms")
    return terms


def get_known_names() -> List[str]:
    """
    Gets a simple list of known names from the reference data.
    """
    name_data = load_people_context()
    names = extract_people_list(name_data)
    logger.info(f"Extracted {len(names)} known Jupiter People")
    return names


if __name__ == "__main__":
    # Test the loading and formatting functions
    print("Testing Jupiter reference data utilities...")

    # Load and display term data
    term_data = load_term_context()
    print(f"\nLoaded {len(term_data.get('terms', []))} terms from reference file")

    # Extract simple term list
    terms_list = extract_terms_list(term_data)
    print(f"Extracted {len(terms_list)} terms (including acronyms)")
    if terms_list:
        print(f"Sample terms: {terms_list[:5]}")

    # Format terms for prompt
    formatted_terms = format_terms_for_prompt(term_data)
    print("\nSample of formatted terms for prompt:")
    print(formatted_terms[:500] + "...\n")

    # Load and display people data
    people_data = load_people_context()
    print(f"\nLoaded {len(people_data.get('people', []))} people from reference file")

    # Extract simple people list
    people_list = extract_people_list(people_data)
    print(f"Extracted {len(people_list)} names (including nicknames)")
    if people_list:
        print(f"Sample names: {people_list[:5]}")

    # Format people for prompt
    formatted_people = format_people_for_prompt(people_data)
    print("\nSample of formatted people for prompt:")
    print(formatted_people[:500] + "...\n")

    # Test the convenience functions
    known_terms = get_known_terms()
    known_names = get_known_names()

    print(f"\nConvenience function get_known_terms() returned {len(known_terms)} terms")
    print(f"Convenience function get_known_names() returned {len(known_names)} names")