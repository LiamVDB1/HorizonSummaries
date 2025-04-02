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

    Args:
        transcript (str): Raw transcript text

    Returns:
        str: Cleaned transcript
    """
    logger.info("Cleaning transcript")

    # Convert to lowercase for consistency in processing
    text = transcript

    # Replace common speech-to-text artifacts
    replacements = {
        # Number formatting
        r'\b(\d+)\.(\d+)\b': r'\1,\2',  # Fix decimal points that should be commas

        # Correct common misheard words or phrases
        r'\bjupyter\b': 'Jupiter',
        r'\bsolana\b': 'Solana',
        r'\betherium\b': 'Ethereum',
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


def split_into_paragraphs(text: str) -> List[str]:
    """
    Split a transcript into logical paragraphs.

    Args:
        text (str): Transcript text

    Returns:
        List[str]: List of paragraphs
    """
    # Split on sentences that appear to be topic transitions
    # Look for patterns like "Moving on to..." or "Let's talk about..." or long pauses
    transition_patterns = [
        r'(?<=[.!?])\s+(?=[A-Z][^.!?]{15,}(?:moving on|next|now|let\'s|turning to|shifting to|talking about|discuss))',
        r'(?<=[.!?])\s+(?=So,\s+[A-Z][^.!?]{10,})',
        r'(?<=[.!?])\s+(?=[A-Z][^.!?]{0,10}(?:first|second|third|fourth|finally|lastly))'
    ]

    paragraphs = [text]
    for pattern in transition_patterns:
        new_paragraphs = []
        for p in paragraphs:
            splits = re.split(pattern, p)
            new_paragraphs.extend(splits)
        paragraphs = new_paragraphs

    # Filter out empty paragraphs and strip whitespace
    return [p.strip() for p in paragraphs if p.strip()]


def identify_speakers(transcript: str) -> Dict[str, List[str]]:
    """
    Attempt to identify different speakers in a transcript.

    Args:
        transcript (str): Transcript text

    Returns:
        Dict[str, List[str]]: Dictionary of speaker -> list of utterances
    """
    # Look for patterns like "Speaker: text" or "Name: text"
    speaker_pattern = r'([A-Z][a-zA-Z\s.]+):\s+([^\n]+(?:\n(?![A-Z][a-zA-Z\s.]+:).*)*)'

    matches = re.findall(speaker_pattern, transcript)

    if not matches:
        # If no explicit speakers found, return the whole transcript as a single speaker
        return {"Unknown": [transcript]}

    speakers = {}
    for speaker, utterance in matches:
        speaker = speaker.strip()
        if speaker not in speakers:
            speakers[speaker] = []
        speakers[speaker].append(utterance.strip())

    return speakers