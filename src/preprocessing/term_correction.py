# src/preprocessing/term_correction.py
"""
Applies term corrections to a transcript using both persisted corrections
from a database and newly identified corrections from an LLM analysis.
"""

import logging
import re
from typing import Dict, Optional, Any

from src.config import Config
from src.utils.logger import setup_logger
from src.database.term_db import (
    get_all_term_corrections,
    add_multiple_term_corrections,
    get_term_corrections_with_metadata
)
from src.llm.term_analyzer import analyze_transcript_for_term_errors
from src.preprocessing.reference_data import (
    load_term_context,
    load_people_context
)

logger = setup_logger(__name__)


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

    # 1. Load reference data
    term_data = load_term_context()
    people_data = load_people_context()

    # 2. First apply high-confidence corrections from the database
    high_confidence_threshold = Config.HIGH_CONFIDENCE_THRESHOLD  # e.g., 0.75
    high_confidence_corrections = get_all_term_corrections(min_confidence=high_confidence_threshold)

    if high_confidence_corrections:
        logger.info(
            f"Applying {len(high_confidence_corrections)} high-confidence existing corrections (confidence >= {high_confidence_threshold})")
        partially_corrected = _apply_corrections(transcript, high_confidence_corrections)
    else:
        logger.info("No high-confidence corrections found in database.")
        partially_corrected = transcript

    # 3. Analyze the partially-corrected transcript with LLM to find new corrections
    llm_correction_data = None

    if term_data.get("terms") or people_data.get("people"):
        try:
            # Use the LLM analyzer with just the reference data (simplified API)
            llm_correction_data = await analyze_transcript_for_term_errors(
                partially_corrected,
                term_data,
                people_data
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