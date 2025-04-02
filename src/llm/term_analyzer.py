"""
AI-powered analysis of terminology in transcripts, with automatic correction of Jupiter-specific terms.
"""

import os
import json
import logging
import sqlite3
from typing import Dict, List, Tuple

from src.config import Config
from src.llm.vertex_ai import VertexAIClient

logger = logging.getLogger("horizon_summaries")

# Known Jupiter terms to use as a reference for the AI to find misspellings
JUPITER_REFERENCE_TERMS = [
    "Jupiter", "JUP", "Jupiverse", "Catdet", "Catdets", "Core Working Group", "CWG",
    "Uplink Working Group", "Catdet Working Group", "CAWG", "Jup & Juice", "DAO", "LFG", "SpaceStation",
    "JupResearch", "ASR", "Active Staking Rewards", "DCA", "Dollar Cost Averaging",
    "Cats of Culture", "CoC", "PPP", "Player Pump Player", "Web3", "Perpetuals",
    "JupSOL", "J4J", "JUP Mobile", "AIWG", "Ape Pro", "Jupiter Horizon",
    "Planetary Call", "Office Hours", "Grant", "Bounty"
]


def get_db_connection() -> sqlite3.Connection:
    """
    Get a connection to the SQLite database for storing term corrections.

    Returns:
        sqlite3.Connection: Connection to the database
    """
    # Ensure data directory exists
    os.makedirs(os.path.dirname(Config.TERMS_DB_PATH), exist_ok=True)

    # Connect to the database
    conn = sqlite3.connect(Config.TERMS_DB_PATH)

    # Create the table if it doesn't exist
    conn.execute('''
        CREATE TABLE IF NOT EXISTS term_corrections (
            incorrect TEXT PRIMARY KEY,
            correct TEXT NOT NULL,
            usage_count INTEGER DEFAULT 1,
            last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    return conn


def load_db_corrections() -> Dict[str, str]:
    """
    Load term corrections from the SQLite database.

    Returns:
        Dict[str, str]: Dictionary of incorrect terms -> correct terms
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get all corrections
        cursor.execute('SELECT incorrect, correct FROM term_corrections')
        corrections = {row[0]: row[1] for row in cursor.fetchall()}

        conn.close()

        logger.info(f"Loaded {len(corrections)} term corrections from database")
        return corrections
    except Exception as e:
        logger.error(f"Error loading term corrections from database: {str(e)}")
        return {}


def save_term_corrections(corrections: Dict[str, str]) -> None:
    """
    Save term corrections to the SQLite database, updating usage counts.

    Args:
        corrections (Dict[str, str]): Dictionary of incorrect terms -> correct terms
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Insert or update each correction
        for incorrect, correct in corrections.items():
            cursor.execute('''
                INSERT INTO term_corrections (incorrect, correct) 
                VALUES (?, ?)
                ON CONFLICT(incorrect) DO UPDATE SET 
                    correct = ?,
                    usage_count = usage_count + 1,
                    last_used = CURRENT_TIMESTAMP
            ''', (incorrect, correct, correct))

        conn.commit()
        conn.close()

        logger.info(f"Saved {len(corrections)} term corrections to database")
    except Exception as e:
        logger.error(f"Error saving term corrections to database: {str(e)}")


async def analyze_transcript_terminology(transcript: str) -> Dict[str, str]:
    """
    Analyze a transcript to identify and correct misspelled Jupiter-specific terms.

    Args:
        transcript (str): The transcript text to analyze

    Returns:
        Dict[str, str]: Dictionary of incorrect terms -> correct terms
    """
    logger.info("Analyzing transcript for terminology")

    # First, load known corrections from the database
    existing_corrections = load_db_corrections()

    # Create prompt for the AI
    prompt = f"""You are a specialized AI that analyzes transcripts from the Jupiter ecosystem to identify and correct misspellings or incorrect usages of Jupiter-specific terminology. 

Here is a list of commonly used Jupiter terms in their correct form:
{json.dumps(JUPITER_REFERENCE_TERMS, indent=2)}

Analyze the following transcript and identify any misspellings or variations of these Jupiter terms. Look for patterns where terms are consistently misspelled or used incorrectly throughout the transcript. Focus only on Jupiter-specific terminology.

TRANSCRIPT:
{transcript[:20000]}  # Limit to avoid token issues

Output ONLY a JSON object mapping the incorrect terms to their correct form, like this:
{{
  "jupitor": "Jupiter",
  "jupe": "JUP",
  "the universe": "the Jupiverse",
  "cat det": "Catdet",
  "dow": "DAO"
}}

Include only terms that are consistently misspelled throughout the transcript. If a term appears both correctly and incorrectly, only include it if the incorrect form is more common. Do not include correct terms, only map from incorrect to correct.
"""

    # Define JSON schema for validation
    json_schema = {
        "type": "object",
        "additionalProperties": {"type": "string"}
    }

    # Get AI response
    client = VertexAIClient()
    corrections = await client.get_json_response(prompt, json_schema)

    # Combine with existing corrections
    if corrections:
        # Merge new corrections with existing ones
        all_corrections = {**existing_corrections, **corrections}

        # Save new corrections to database
        save_term_corrections(corrections)

        logger.info(f"Found {len(corrections)} new term corrections in transcript")
    else:
        all_corrections = existing_corrections
        logger.info("No new term corrections found in transcript")

    return all_corrections


def correct_terms_in_transcript(transcript: str, corrections: Dict[str, str]) -> str:
    """
    Apply term corrections to a transcript.

    Args:
        transcript (str): The transcript text
        corrections (Dict[str, str]): Dictionary of incorrect terms -> correct terms

    Returns:
        str: Transcript with terms corrected
    """
    # Sort corrections by length (longest first) to avoid partial replacements
    sorted_corrections = sorted(
        corrections.items(),
        key=lambda x: len(x[0]),
        reverse=True
    )

    # Apply each correction
    corrected_text = transcript
    for incorrect, correct in sorted_corrections:
        # Case-insensitive replacement that preserves case
        # If the original is all caps, make the replacement all caps
        # If the original is title case, make the replacement title case (respecting compound words)
        # Otherwise, use the correct form as-is

        # Replace exact matches
        corrected_text = corrected_text.replace(incorrect, correct)

        # Replace case variations
        if incorrect.lower() != incorrect:
            # Replace lowercase version
            corrected_text = corrected_text.replace(incorrect.lower(), correct.lower())

            # Replace uppercase version
            corrected_text = corrected_text.replace(incorrect.upper(), correct.upper())

            # Replace title case version (considering compound words)
            incorrect_title = ' '.join(word.capitalize() for word in incorrect.split())
            correct_title = ' '.join(word.capitalize() for word in correct.split())
            corrected_text = corrected_text.replace(incorrect_title, correct_title)

    return corrected_text