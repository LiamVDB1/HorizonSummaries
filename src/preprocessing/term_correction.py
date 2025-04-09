# src/preprocessing/term_correction.py
"""
Applies term corrections to a transcript using both persisted corrections
from a database and newly identified corrections from an LLM analysis.
"""

import logging
import json
import re
from typing import List, Dict, Optional, Any

from src.config import Config
from src.utils.logger import setup_logger
from src.database.term_db import (
    get_all_term_corrections,
    add_multiple_term_corrections,
    get_term_corrections_with_metadata
)
from src.llm.term_analyzer import analyze_transcript_for_term_errors

logger = setup_logger(__name__)


def _load_known_terms() -> List[str]:
    """Loads the list of known correct Jupiter terms from the resource file."""
    try:
        if Config.JUPITER_TERMS_FILE.exists():
            with open(Config.JUPITER_TERMS_FILE, 'r') as f:
                data = json.load(f)
                terms = data.get("terms", [])
                if isinstance(terms, list) and all(isinstance(t, str) for t in terms):
                    logger.info(f"Loaded {len(terms)} known Jupiter terms from {Config.JUPITER_TERMS_FILE}")
                    return terms
                else:
                    logger.error(
                        f"Invalid format in {Config.JUPITER_TERMS_FILE}. Expected a list of strings under the 'terms' key.")
                    return []
        else:
            logger.warning(
                f"Known terms file not found: {Config.JUPITER_TERMS_FILE}. Term analysis may be less effective.")
            return []
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from {Config.JUPITER_TERMS_FILE}.")
        return []
    except Exception as e:
        logger.error(f"Error loading known terms: {e}", exc_info=True)
        return []


def _load_known_names() -> List[str]:
    """Loads the list of known person names from the resource file."""
    try:
        if Config.JUPITER_NAMES_FILE.exists():
            with open(Config.JUPITER_NAMES_FILE, 'r') as f:
                data = json.load(f)
                names = data.get("names", [])
                if isinstance(names, list) and all(isinstance(n, str) for n in names):
                    logger.info(f"Loaded {len(names)} known Jupiter names from {Config.JUPITER_NAMES_FILE}")
                    return names
                else:
                    logger.error(
                        f"Invalid format in {Config.JUPITER_NAMES_FILE}. Expected a list of strings under the 'names' key.")
                    return []
        else:
            logger.warning(f"Known names file not found: {Config.JUPITER_NAMES_FILE}")
            return []
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from {Config.JUPITER_NAMES_FILE}.")
        return []
    except Exception as e:
        logger.error(f"Error loading known names: {e}", exc_info=True)
        return []


def _apply_corrections(transcript: str, corrections: Dict[str, str]) -> str:
    """
    Applies a dictionary of corrections to the transcript.

    Args:
        transcript (str): The transcript text to correct.
        corrections (Dict[str, str]): Dictionary of {incorrect: correct} terms.

    Returns:
        str: The corrected transcript.
    """
    if not corrections:
        return transcript

    corrected = transcript
    for incorrect, correct in corrections.items():
        if not incorrect or not correct:
            continue

        # Use regex for case-insensitive replacement with word boundaries
        pattern = r'\b' + re.escape(incorrect) + r'\b'
        corrected = re.sub(pattern, correct, corrected, flags=re.IGNORECASE)

    return corrected


async def correct_jupiter_terms(transcript: str) -> str:
    """
    Corrects Jupiter-specific terminology in the transcript using AI analysis
    and a persistent database of corrections.

    The process:
    1. Apply high-confidence existing corrections from the database
    2. Send the partially-corrected transcript to the LLM for analysis
    3. Store any new corrections in the database
    4. Apply medium and low confidence corrections that don't conflict

    Args:
        transcript (str): The transcript text to process.

    Returns:
        str: The transcript with corrections applied.
    """
    if not transcript:
        return ""

    logger.info("Starting Jupiter term correction process...")

    # 1. Load known reference data
    known_terms = _load_known_terms()
    known_names = _load_known_names()

    # 2. First apply high-confidence corrections from the database
    high_confidence_threshold = Config.HIGH_CONFIDENCE_THRESHOLD  # e.g., 0.75
    high_confidence_corrections = get_all_term_corrections(min_confidence=high_confidence_threshold)

    if high_confidence_corrections:
        logger.info(f"Applying {len(high_confidence_corrections)} high-confidence existing corrections (confidence >= {high_confidence_threshold})")
        partially_corrected = _apply_corrections(transcript, high_confidence_corrections)
    else:
        logger.info("No high-confidence corrections found in database.")
        partially_corrected = transcript

    # 3. Analyze the partially-corrected transcript with LLM to find new corrections
    llm_correction_data = None

    if known_terms or known_names:
        try:
            llm_correction_data = await analyze_transcript_for_term_errors(
                partially_corrected,
                known_terms,
                known_names
            )

            if llm_correction_data:
                logger.info(f"LLM analysis suggested {len(llm_correction_data)} potential corrections.")

                # Store all corrections in the database (even low confidence ones)
                add_multiple_term_corrections(llm_correction_data)

                # Filter for immediate application based on confidence
                high_confidence_new = {}
                for incorrect, data in llm_correction_data.items():
                    if data.get('confidence', 0) >= high_confidence_threshold:
                        high_confidence_new[incorrect] = data['term']

                if high_confidence_new:
                    logger.info(f"Applying {len(high_confidence_new)} new high-confidence corrections")
                    partially_corrected = _apply_corrections(partially_corrected, high_confidence_new)
            else:
                logger.info("LLM analysis did not suggest any new term corrections.")
        except Exception as e:
            logger.error(f"LLM term analysis failed: {e}", exc_info=True)

    # 4. Now apply medium-confidence corrections from the database that weren't already applied
    medium_confidence_threshold = Config.MEDIUM_CONFIDENCE_THRESHOLD  # e.g., 0.6

    # Get all corrections between medium and high thresholds
    all_corrections = get_term_corrections_with_metadata(
        min_confidence=medium_confidence_threshold
    )

    # Filter out corrections that have already been applied
    medium_corrections = {}
    for incorrect, data in all_corrections.items():
        confidence = data.get('confidence', 0)
        # Only include medium confidence corrections not already in high confidence list
        if medium_confidence_threshold <= confidence < high_confidence_threshold:
            if incorrect not in high_confidence_corrections:
                medium_corrections[incorrect] = data['term']

    if medium_corrections:
        logger.info(
            f"Applying {len(medium_corrections)} medium-confidence corrections (confidence between {medium_confidence_threshold} and {high_confidence_threshold})")
        final_transcript = _apply_corrections(partially_corrected, medium_corrections)
    else:
        final_transcript = partially_corrected

    logger.info("Finished applying term corrections.")
    return final_transcript