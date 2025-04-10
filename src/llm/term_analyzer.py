"""
Uses Vertex AI to analyze transcripts and identify potential misspellings
or variations of known Jupiter-related terms.
"""

import logging
from typing import List, Dict, Optional, Any

from src.config import Config
from src.llm.vertex_ai import VertexAIGenerator
from src.preprocessing.reference_data import format_terms_for_prompt, format_people_for_prompt, extract_terms_list, \
    extract_people_list
from src.utils.logger import setup_logger
from src.utils.json_parser import parse_json_from_llm

logger = setup_logger(__name__)

async def analyze_transcript_for_term_errors(
    transcript: str,
    term_data: Dict[str, Any],
    people_data: Dict[str, Any],
    model_name: str = Config.TERM_ANALYSIS_MODEL
) -> Optional[Dict[str, Dict[str, Any]]]:
    """
    Analyzes a transcript using an LLM to find likely misspellings or incorrect
    phrasings of known terms and suggests corrections.

    Args:
        transcript (str): The transcript text to analyze.
        term_data (Dict[str, Any]): Rich term context data.
        people_data (Dict[str, Any]): Rich name context data.
        model_name (str): The Vertex AI model to use for analysis.

    Returns:
        Optional[Dict[str, Dict[str, Any]]]: A dictionary mapping
            { "incorrect_term": {"term": "correct_term", "confidence": 0.9, ...} }
            based on the LLM's analysis, or None if analysis fails
            or no corrections are found.
    """
    if not transcript:
        logger.warning("Transcript is empty, skipping term analysis.")
        return None

    # Extract simplified lists for validation (moved from parameters to internal extraction)
    known_terms = extract_terms_list(term_data)
    known_people = extract_people_list(people_data)

    if not known_terms and not known_people:
        logger.warning("Both known terms and people lists are empty, skipping term analysis.")
        return None

    logger.info(f"Starting term analysis with model: {model_name}")

    # Format the rich context data for the prompt
    terms_context = format_terms_for_prompt(term_data)
    people_context = format_people_for_prompt(people_data)

    # --- Enhanced Prompt Engineering with Full Context ---
    prompt = f"""
Analyze the following transcript for potential misspellings, mishearings, or incorrect variations of Jupiter ecosystem terms and people.

{terms_context}

{people_context}

**Transcript:**
```
{transcript}
```

**Instructions:**
1. Read through the transcript carefully.
2. Identify words or phrases that seem like incorrect versions of Jupiter Terms or Jupiter people's names.
3. For each identified incorrect term:
   - Determine the most likely correct term from the provided reference data
   - Assign a confidence score (0.0-1.0) based on your certainty
   - Provide brief reasoning for your correction and confidence score
   - Identify the type of correction ('term', 'person', 'acronym')
4. Respond ONLY with a valid JSON object in this format:
```json
{{
  "incorrect_term": {{
    "term": "correct_term", 
    "confidence": 0.0 <= confidence_score <= 1.0,
    "reasoning": "Brief explanation of why this correction was made",
    "correction_type": "term"
  }}
}}
```

**Examples:**
- "Jupyter": {{
    "term": "Jupiter", 
    "confidence": 0.95,
    "reasoning": "Clear misspelling of the platform name, appears multiple times",
    "correction_type": "term"
  }}
- "Jupin Juice": {{
    "term": "Jup & Juice", 
    "confidence": 0.90,
    "reasoning": "Common mishearing of the podcast name, context confirms this is the podcast",
    "correction_type": "term"
  }}
- "perp dex": {{
    "term": "Perps", 
    "confidence": 0.85,
    "reasoning": "Generic reference to Jupiter's perpetual futures product",
    "correction_type": "term"
  }}
- "Constantinos": {{
    "term": "Konstantinos", 
    "confidence": 0.88,
    "reasoning": "Based on context, appears to be referring to the Devrel Working group member",
    "correction_type": "person"
  }}
- "Siong Li" → {{
    "term": "Siong", 
    "confidence": 0.92,
    "reasoning": "Referencing the Co-founder by full name instead of common name",
    "correction_type": "person"
  }}

**Important Guidelines:**
- Consider how the term is used in context
- Terms that appear multiple times incorrectly should have higher confidence
- Be careful with ambiguous terms that could have multiple meanings (e.g., acronyms)
- Watch for playful name variations that might be intentional (assign lower confidence)
- Do not correct terms that appear to be intentional variations or jokes
- Consider the frequency of appearance for confidence scoring
- Pay attention to surrounding context when choosing between ambiguous corrections

**JSON Response:**
"""

    # System instruction for term analysis
    system_instruction = """You are an AI assistant specialized in analyzing text transcripts from the Solana and Jupiter ecosystem. Your task is to identify and correct misspellings or variations of specific known terms and names based on the comprehensive reference data provided. You must output your findings strictly as a JSON object mapping incorrect terms to detailed correction information including confidence scores and reasoning."""

    try:
        generator = VertexAIGenerator()
        # Generate the analysis using the core vertex_ai function
        llm_output = await generator.generate_response_with_retry(
            prompt=prompt,
            model=model_name,
            temperature=0.2,  # Lower temperature for more deterministic analysis
            max_output_tokens=4096,  # Increased for detailed responses with rich context
            system_instruction=system_instruction
        )

        raw_llm_output = llm_output.get("content", "")

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

        # Validate the structure of the corrections
        valid_corrections = {}
        for incorrect_term, correction_data in corrections.items():
            # Skip if the correction data isn't a dictionary
            if not isinstance(correction_data, dict):
                logger.warning(f"Invalid correction format for '{incorrect_term}': {correction_data}")
                continue

            # Ensure required fields are present
            if 'term' not in correction_data:
                logger.warning(f"Missing 'term' field for '{incorrect_term}'")
                continue

            # Set defaults for optional fields if missing
            if 'confidence' not in correction_data:
                correction_data['confidence'] = 0.7  # Default medium confidence

            if 'correction_type' not in correction_data:
                # Try to auto-detect if it's a person name
                if known_people and correction_data['term'] in known_people:
                    correction_data['correction_type'] = 'person'
                else:
                    correction_data['correction_type'] = 'term'

            valid_corrections[incorrect_term] = correction_data

        logger.info(f"Term analysis identified {len(valid_corrections)} potential corrections.")
        logger.debug(f"Identified corrections: {valid_corrections}")
        return valid_corrections

    except Exception as e:
        logger.error(f"Error during term analysis LLM call: {e}", exc_info=True)
        return None