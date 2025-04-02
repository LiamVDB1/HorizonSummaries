# src/llm/topic_extractor.py
"""
Uses Vertex AI to extract key topics from a transcript.
"""

import logging
import json
from typing import List, Optional

from src.config import Config
from src.llm.vertex_ai import generate_text, parse_json_from_llm, initialize_vertex_ai
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# Initialize Vertex AI
initialize_vertex_ai()

async def extract_topics_llm(
    transcript: str,
    model_name: str = Config.TOPIC_EXTRACTION_MODEL,
    max_topics: int = 10 # Limit the number of topics
) -> Optional[List[str]]:
    """
    Extracts key topics from a transcript using an LLM.

    Args:
        transcript (str): The transcript text to analyze.
        model_name (str): The Vertex AI model to use.
        max_topics (int): Approximate maximum number of topics to return.

    Returns:
        Optional[List[str]]: A list of key topics identified by the LLM,
                             or None if extraction fails.
    """
    if not transcript:
        logger.warning("Transcript is empty, skipping topic extraction.")
        return None

    logger.info(f"Starting topic extraction with model: {model_name}")

    # --- Prompt Engineering ---
    prompt = f"""
Analyze the following transcript and identify the main topics discussed.

**Transcript:**
```
{transcript}
```

**Instructions:**
1. Read the transcript carefully to understand the key subjects and themes.
2. Identify the most important topics covered. Aim for concise topic labels (1-4 words).
3. List the main topics, focusing on specific subjects, projects, announcements, or discussions.
4. Return ONLY a valid JSON list of strings, where each string is a distinct topic.
5. Aim for approximately {max_topics} topics, but adjust based on the content's density. Do not include generic topics like "Q&A" unless it was a major segment.
6. If the transcript is too short or lacks clear topics, return an empty JSON list: [].

**Example Output Format:**
```json
[
  "LFG Launchpad Updates",
  "Perpetual Futures Market",
  "Metropolis Part 2",
  "Community Governance Proposal",
  "Integration with Zeus Network",
  "Upcoming Tokenomics Changes"
]
```

**JSON Response:**
"""

    # System instruction for topic extraction
    system_instruction = """You are an AI assistant skilled at identifying key topics within lengthy text documents, specifically transcripts related to blockchain projects like Jupiter. Your goal is to extract a concise list of the most relevant subjects discussed. Output must be a JSON list of strings."""

    try:
        raw_llm_output = await generate_text(
            prompt=prompt,
            model_name=model_name,
            temperature=0.3, # Moderate temperature for topic identification
            max_output_tokens=512, # Usually enough for a list of topics
            system_instruction=system_instruction
        )

        if not raw_llm_output:
            logger.warning("Topic extraction LLM returned an empty response.")
            return None

        # Parse the JSON list
        topics = parse_json_from_llm(raw_llm_output, description="topic extraction")

        if topics is None:
            logger.error("Failed to parse JSON topics from LLM response.")
            return None

        if not isinstance(topics, list):
            logger.error(f"Topic extraction LLM response was not a valid list: {topics}")
            return None

        # Validate that elements are strings (basic check)
        if not all(isinstance(topic, str) for topic in topics):
             logger.error(f"Topic list contains non-string elements: {topics}")
             # Attempt to filter or return None
             valid_topics = [str(t) for t in topics if isinstance(t, (str, int, float))] # Be lenient?
             if len(valid_topics) != len(topics):
                 logger.warning("Filtered non-string elements from topic list.")
             topics = valid_topics
             if not topics: return None # Return None if filtering removed everything

        logger.info(f"Topic extraction identified {len(topics)} topics.")
        logger.debug(f"Extracted topics: {topics}")
        return topics

    except Exception as e:
        logger.error(f"Error during topic extraction LLM call: {e}", exc_info=True)
        return None

