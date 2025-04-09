"""
Functions for cleaning and preprocessing transcripts.
"""

import re
import logging
from typing import Dict, List

logger = logging.getLogger("horizon_summaries")

# Common filler words and phrases to clean up
FILLER_WORDS = [
    r'\bum\b', r'\buh\b', r'\ber\b', r'\blike\b(?!\s+to|\s+I|\s+we|\s+they|\s+you)',
    r'\byou know\b', r'\bkind of\b', r'\bsort of\b', r'\bi mean\b',
    r'\bbasically\b', r'\bliterally\b', r'\bactually\b', r'\breally\b',
    r'\bjust\b', r'\bso\b(?!\s+that|\s+I|\s+we|\s+they|\s+you)'
]

# Speaking disfluencies patterns
DISFLUENCIES = [
    r'(\w+)(\s+\1){1,}',  # Repeated words
    r'(\w+\s+){1,2}(?:I|we|you|they|he|she|it)(\s+\1){1,}',  # Phrase repetitions
]

# Hesitation and pause markers
HESITATIONS = [
    r'\.{2,}', r'-{2,}', r'…'
]


def clean_transcript(transcript: str) -> str:
    """
    Clean and normalize a transcript to improve readability.
    Handles basic cleanup of transcription artifacts, disfluencies, and formatting.
    Does NOT handle Jupiter-specific term corrections (that's done separately).

    Args:
        transcript (str): Raw transcript text

    Returns:
        str: Cleaned transcript
    """
    logger.info("Cleaning transcript")

    text = transcript

    # Replace common speech-to-text artifacts
    replacements = {
        # Number formatting
        r'\b(\d+)\.(\d+)\b': r'\1,\2',  # Fix decimal points that should be commas

        # Only the most universal transcription corrections
        # (Jupiter-specific corrections are handled by term_correction.py)
        r'\bweb tree\b': 'web3',

        # Fix common punctuation issues
        r'(?<=[.!?])\s+(?=[a-z])': lambda m: m.group(0).upper(),  # Capitalize after periods
        r'\s+([,.;:!?])': r'\1',  # Remove space before punctuation

        # Fix quotation marks
        r'(?<=\w)"(?=\s|$)': '"',  # Close quotes properly
        r'(?<=\s|^)"(?=\w)': '"',  # Open quotes properly
    }

    # Apply replacements
    for pattern, replacement in replacements.items():
        if callable(replacement):
            text = re.sub(pattern, replacement, text)
        else:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # Remove filler words
    for filler in FILLER_WORDS:
        text = re.sub(filler, '', text, flags=re.IGNORECASE)

    # Fix disfluencies (repeated words)
    for pattern in DISFLUENCIES:
        text = re.sub(pattern, r'\1', text)

    # Normalize hesitations and pauses
    for pattern in HESITATIONS:
        text = re.sub(pattern, '. ', text)

    # Fix multiple spaces
    text = re.sub(r'\s+', ' ', text)

    # Fix multiple periods
    text = re.sub(r'\.+', '.', text)

    # Ensure proper spacing around punctuation
    text = re.sub(r'(\w)([,.;:!?])(\w)', r'\1\2 \3', text)

    # Ensure sentences start with capital letters
    text = re.sub(r'(?<=[.!?]\s)([a-z])', lambda m: m.group(1).upper(), text)

    # Fix spacing in common abbreviations
    text = re.sub(r'(?<=\w)\.(?=\w)', '. ', text)

    # Final cleanup of any remaining whitespace issues
    text = re.sub(r'\s+', ' ', text).strip()

    logger.info(f"Transcript cleaned: {len(transcript)} -> {len(text)} characters")
    return text