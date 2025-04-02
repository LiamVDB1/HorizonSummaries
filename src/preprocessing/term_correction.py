"""
Functions for correcting Jupiter-specific terms in transcripts.
"""

import re
import json
import logging
from typing import Dict, List

from src.config import Config
from src.utils.file_handling import read_json, ensure_directory

logger = logging.getLogger("horizon_summaries")

# Default Jupiter terms corrections if the JSON file is not available
DEFAULT_TERMS = {
    "jup": "JUP",
    "jup token": "JUP token",
    "jupiter": "Jupiter",
    "jupyter": "Jupiter",
    "jupitor": "Jupiter",
    "the dow": "the DAO",
    "dow": "DAO",
    "solana": "Solana",
    "cat det": "Catdet",
    "catdets": "Catdets",
    "cat dets": "Catdets",
    "cap det": "Catdet",
    "cap dets": "Catdets",
    "jupe ai": "JUP AI",
    "jupe-ai": "JUP AI",
    "jupe": "JUP",
    "the universe": "the Jupiverse",
    "universe": "Jupiverse",
    "jup and juice": "Jup & Juice",
    "j. for j.": "J4J",
    "jay for jay": "J4J",
    "core working group": "Core Working Group",
    "cwg": "CWG",
    "uplink working group": "Uplink Working Group",
    "uplink": "Uplink Working Group",
    "lfg launchpad": "LFG Launchpad",
    "lfg": "LFG",
    "planetary call": "Planetary Call",
    "asr": "ASR",
    "active staking rewards": "Active Staking Rewards",
    "decca": "DCA",
    "dollar cost averaging": "Dollar Cost Averaging",
    "the space station": "the SpaceStation",
    "space station": "SpaceStation",
    "jupe research": "JupResearch",
    "jupe-research": "JupResearch",
    "cats of culture": "Cats of Culture",
    "coc": "CoC",
    "ppp": "PPP",
    "player pump player": "Player Pump Player",
    "web three": "Web3",
    "web 3": "Web3",
    "gemini pro": "Gemini Pro",
    "claude opus": "Claude Opus",
    "horizon ai": "Horizon AI",
    "jupiter horizon": "Jupiter Horizon",
    "horizon": "Jupiter Horizon",
    "gpt four": "GPT-4",
    "gpt-four": "GPT-4"
}


def load_jupiter_terms() -> Dict[str, str]:
    """
    Load Jupiter-specific terms from a JSON file or use defaults.

    Returns:
        Dict[str, str]: Dictionary of incorrect terms -> correct terms
    """
    try:
        # Try to load the terms from the JSON file
        terms = read_json(Config.JUPITER_TERMS_FILE)
        logger.info(f"Loaded Jupiter terms from {Config.JUPITER_TERMS_FILE}: {len(terms)} terms")
        return terms
    except (FileNotFoundError, json.JSONDecodeError) as e:
        # If the file doesn't exist or is invalid, use the default terms and save them
        logger.warning(f"Jupiter terms file not found or invalid: {str(e)}")
        logger.info("Using default Jupiter terms")

        # Save the default terms for future use
        try:
            ensure_directory(Config.RESOURCES_DIR)
            with open(Config.JUPITER_TERMS_FILE, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_TERMS, f, indent=2)
            logger.info(f"Saved default Jupiter terms to {Config.JUPITER_TERMS_FILE}")
        except Exception as save_error:
            logger.warning(f"Failed to save default Jupiter terms: {str(save_error)}")

        return DEFAULT_TERMS


def build_terms_regex() -> re.Pattern:
    """
    Build a regex pattern for Jupiter terms.

    Returns:
        re.Pattern: Compiled regex pattern
    """
    terms = load_jupiter_terms()
    pattern = r'\b(?:' + '|'.join(map(re.escape, terms.keys())) + r')\b'
    return re.compile(pattern, re.IGNORECASE)


def correct_jupiter_terms(transcript: str) -> str:
    """
    Correct Jupiter-specific terms in a transcript.

    Args:
        transcript (str): The transcript text

    Returns:
        str: Transcript with corrected terms
    """
    logger.info("Correcting Jupiter-specific terms")

    terms = load_jupiter_terms()

    def replace_term(match):
        matched_term = match.group(0)
        # Find the correct replacement, handling case-insensitivity
        for incorrect, correct in terms.items():
            if matched_term.lower() == incorrect.lower():
                # Check if the original was uppercase
                if matched_term.isupper():
                    return correct.upper()
                # Check if the original was title case
                elif matched_term.istitle():
                    return correct.title() if ' ' not in correct else correct
                # Otherwise, use the correct term as-is
                else:
                    return correct
        return matched_term

    # Build the regex pattern
    pattern = build_terms_regex()

    # Apply the corrections
    corrected = pattern.sub(replace_term, transcript)

    # Count the number of corrections
    corrections_count = sum(1 for i, j in zip(transcript, corrected) if i != j)
    logger.info(f"Made {corrections_count} term corrections")

    return corrected


def suggest_term_additions(transcript: str) -> List[str]:
    """
    Suggest new terms that might need to be added to the Jupiter terms list.

    Args:
        transcript (str): The transcript text

    Returns:
        List[str]: List of potential new terms
    """
    # Look for terms that might be Jupiter-related but aren't in our dictionary
    # This could include:
    # 1. Words that frequently appear with "Jupiter" or "JUP"
    # 2. Capitalized multi-word phrases that appear multiple times
    # 3. Technical terms related to blockchain/crypto that might be misspelled

    jupiter_context_pattern = r'(?:Jupiter|JUP)\s+([A-Z][a-zA-Z]+)'
    capitalized_phrases_pattern = r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)+)\b'

    # Find terms in Jupiter context
    jupiter_context_terms = re.findall(jupiter_context_pattern, transcript)

    # Find capitalized phrases
    capitalized_phrases = re.findall(capitalized_phrases_pattern, transcript)

    # Combine and return unique terms
    return list(set(jupiter_context_terms + capitalized_phrases))