"""
Uses Vertex AI to analyze transcripts and identify potential misspellings
or variations of known Jupiter-related terms.
"""

import logging
import json
from typing import List, Dict, Optional

from src.config import Config
from src.llm.vertex_ai import generate_text, parse_json_from_llm, initialize_vertex_ai
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# Initialize Vertex AI if it hasn't been already
# This ensures it's ready when functions here are called.
# Consider a more central initialization point in main.py if preferred.
initialize_vertex_ai()

async def analyze_transcript_for_term_errors(
    transcript: str,
    known_terms: List[str],
    model_name: str = Config.TERM_ANALYSIS_MODEL
) -> Optional[Dict[str, str]]:
    """
    Analyzes a transcript using an LLM to find likely misspellings or incorrect
    phrasings of known terms and suggests corrections.

    Args:
        transcript (str): The transcript text to analyze.
        known_terms (List[str]): A list of correct Jupiter-related terms.
        model_name (str): The Vertex AI model to use for analysis.

    Returns:
        Optional[Dict[str, str]]: A dictionary mapping { "incorrect_term": "correct_term" }
                                  based on the LLM's analysis, or None if analysis fails
                                  or no corrections are found.
    """
    if not transcript:
        logger.warning("Transcript is empty, skipping term analysis.")
        return None
    if not known_terms:
        logger.warning("Known terms list is empty, skipping term analysis.")
        return None

    logger.info(f"Starting term analysis with model: {model_name}")

    # --- Prompt Engineering ---
    # Provide clear instructions and the desired output format (JSON)
    prompt = f"""
Analyze the following transcript for potential misspellings, mishearings, or incorrect variations of the provided known Jupiter ecosystem terms.

**Known Correct Terms:**
{', '.join(known_terms)}

**Transcript:**
```
{transcript}
```

**Instructions:**
1. Read through the transcript carefully.
2. Identify words or short phrases in the transcript that seem like incorrect versions of the "Known Correct Terms". Focus on terms that appear consistently misspelled or phrased incorrectly.
3. For each identified incorrect term, determine the most likely correct term from the provided list.
4. Respond ONLY with a valid JSON object mapping the incorrect term found in the transcript (key) to its corresponding correct term (value).
5. If no significant or consistent errors related to the known terms are found, respond with an empty JSON object: {{}}.
6. Do not include terms that are already spelled correctly.
7. The keys in the JSON should be the exact incorrect strings as they appear in the transcript.

**Example Output Format:**
```json
{{
  "Jupper": "Jupiter",
  "perp dex": "Perps",
  "limit orders": "Limit Order",
  "metropol": "Metropolis"
}}
```

**JSON Response:**
"""

    # Define a system instruction specific to this task
    system_instruction = """You are an AI assistant specialized in analyzing text transcripts from the Solana and Jupiter ecosystem. Your task is to identify and correct misspellings or variations of specific known terms based on a provided list. You must output your findings strictly as a JSON object mapping incorrect terms to correct terms."""

    try:
        # Generate the analysis using the core vertex_ai function
        raw_llm_output = await generate_text(
            prompt=prompt,
            model_name=model_name,
            temperature=0.2, # Lower temperature for more deterministic analysis
            max_output_tokens=1024, # Adjust as needed
            system_instruction=system_instruction
            # Add safety settings if needed
        )

        if not raw_llm_output:
            logger.warning("Term analysis LLM returned an empty response.")
            return None

        # Parse the JSON response
        corrections = parse_json_from_llm(raw_llm_output, description="term analysis")

        if corrections is None:
            logger.error("Failed to parse JSON corrections from term analysis LLM response.")
            return None

        if not isinstance(corrections, dict):
            logger.error(f"Term analysis LLM response was not a valid dictionary: {corrections}")
            return None

        # Optional: Add filtering based on confidence or frequency if the LLM provided it
        # (Requires adjusting the prompt and parsing logic)

        logger.info(f"Term analysis identified {len(corrections)} potential corrections.")
        logger.debug(f"Identified corrections: {corrections}")
        return corrections

    except Exception as e:
        logger.error(f"Error during term analysis LLM call: {e}", exc_info=True)
        return None

