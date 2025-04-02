# src/preprocessing/term_correction.py
"""
Applies term corrections to a transcript using both persisted corrections
from a database and newly identified corrections from an LLM analysis.
"""

import logging
import json
import re
from typing import List, Dict, Optional

from src.config import Config
from src.utils.logger import setup_logger
from src.database.term_db import get_all_term_corrections, add_multiple_term_corrections
from src.llm.term_analyzer import analyze_transcript_for_term_errors # Async function

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
                    logger.error(f"Invalid format in {Config.JUPITER_TERMS_FILE}. Expected a list of strings under the 'terms' key.")
                    return []
        else:
            logger.warning(f"Known terms file not found: {Config.JUPITER_TERMS_FILE}. Term analysis may be less effective.")
            return []
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from {Config.JUPITER_TERMS_FILE}.")
        return []
    except Exception as e:
        logger.error(f"Error loading known terms: {e}", exc_info=True)
        return []

async def correct_jupiter_terms(transcript: str) -> str:
    """
    Corrects Jupiter-specific terminology in the transcript using AI analysis
    and a persistent database of corrections.

    Args:
        transcript (str): The transcript text to process.

    Returns:
        str: The transcript with corrections applied.
    """
    if not transcript:
        return ""

    logger.info("Starting Jupiter term correction process...")

    # 1. Load known correct terms
    known_terms = _load_known_terms()

    # 2. Analyze transcript with LLM (async)
    llm_corrections: Optional[Dict[str, str]] = None
    if known_terms: # Only run LLM analysis if we have known terms to check against
        try:
            llm_corrections = await analyze_transcript_for_term_errors(transcript, known_terms)
            if llm_corrections:
                logger.info(f"LLM analysis suggested {len(llm_corrections)} new corrections.")
                # 3. Add newly identified corrections to the database
                add_multiple_term_corrections(llm_corrections)
            else:
                logger.info("LLM analysis did not suggest any new term corrections.")
        except Exception as e:
            logger.error(f"LLM term analysis failed: {e}", exc_info=True)
            # Continue without LLM suggestions for this run
            llm_corrections = {} # Ensure it's an empty dict, not None
    else:
        logger.warning("Skipping LLM term analysis as no known terms were loaded.")
        llm_corrections = {}


    # 4. Retrieve all corrections from the database (including newly added ones)
    # We get ALL corrections every time to ensure consistency
    all_db_corrections = get_all_term_corrections()
    if not all_db_corrections:
        logger.info("No term corrections found in the database. Transcript remains unchanged.")
        # If LLM also found nothing, we can return early
        if not llm_corrections:
             return transcript

    # Combine corrections if needed (DB is usually the superset now)
    # The DB retrieval is ordered by length desc, which is good for replacement.
    corrections_to_apply = all_db_corrections
    logger.info(f"Applying {len(corrections_to_apply)} term corrections from database.")


    # 5. Apply corrections to the transcript
    corrected_transcript = transcript
    applied_count = 0
    # Iterate through corrections (already sorted by length desc in get_all_term_corrections)
    for incorrect, correct in corrections_to_apply.items():
        # Use regex for case-insensitive replacement and ensure whole words/phrases
        # \b ensures we match word boundaries, preventing partial matches like "perp" in "perpendicular"
        # We escape the incorrect term in case it contains regex special characters.
        # We use re.IGNORECASE for case-insensitivity.
        pattern = r'\b' + re.escape(incorrect) + r'\b'
        # Use a lambda function in re.sub to preserve the original case of the first letter
        # if the correct term is capitalized (e.g., "jupiter" -> "Jupiter")
        # This is a simple heuristic and might need refinement.
        def replace_match(match):
            nonlocal applied_count
            applied_count += 1
            # Simple case preservation: if correct term starts with capital, capitalize the match
            # This might not be perfect for all cases (e.g., acronyms)
            if correct and correct[0].isupper():
                 # Basic capitalization of the first letter of the match
                 # This might not handle multi-word matches perfectly if complex casing is needed
                 original_match_text = match.group(0)
                 # A simpler approach might be to just return the 'correct' term directly
                 # return correct
                 # Let's try returning the 'correct' term directly for simplicity now
                 return correct
            else:
                # Return the 'correct' term as is (likely lowercase)
                return correct

        # Perform the substitution
        # Using re.sub with a function allows counting actual replacements, but is slower.
        # For performance, a simple re.sub(pattern, correct, corrected_transcript, flags=re.IGNORECASE) might be faster if counting isn't critical per replacement.
        # Let's stick to the simpler version for now:
        new_transcript = re.sub(pattern, correct, corrected_transcript, flags=re.IGNORECASE)
        if new_transcript != corrected_transcript:
             # Count occurrences replaced by comparing lengths or using finditer if needed precisely
             # For now, just log that *a* replacement happened for this rule
             logger.debug(f"Applied correction: '{incorrect}' -> '{correct}'")
             corrected_transcript = new_transcript
             # Note: This doesn't count *how many* times the rule was applied in one go.


    # logger.info(f"Applied approximately {applied_count} term corrections in total.") # This count isn't accurate with simple re.sub
    logger.info("Finished applying term corrections.")
    return corrected_transcript

