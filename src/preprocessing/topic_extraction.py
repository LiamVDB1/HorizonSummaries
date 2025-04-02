"""
Extracts topics from a transcript using an AI model.
"""
import logging
from typing import List, Optional

from src.utils.logger import setup_logger
from src.llm.topic_extractor import extract_topics_llm # Async function

logger = setup_logger(__name__)

async def extract_topics(transcript: str) -> List[str]:
    """
    Identifies key topics in the transcript using an LLM.

    Args:
        transcript (str): The transcript text.

    Returns:
        List[str]: A list of identified topics, or an empty list if none are found or an error occurs.
    """
    logger.info("Extracting topics using LLM...")
    if not transcript:
        logger.warning("Transcript is empty, cannot extract topics.")
        return []

    try:
        topics = await extract_topics_llm(transcript)
        if topics is None:
            # Error logged within extract_topics_llm
            return [] # Return empty list on failure
        logger.info(f"Successfully extracted {len(topics)} topics.")
        return topics
    except Exception as e:
        # Catch potential exceptions from the async call itself
        logger.error(f"An unexpected error occurred during topic extraction: {e}", exc_info=True)
        return []

