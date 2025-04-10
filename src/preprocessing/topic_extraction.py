"""
Extracts topics from a transcript using an AI model.
"""
import logging
from typing import List, Dict, Any, Optional

from src.utils.logger import setup_logger
from src.llm.topic_extractor import extract_topics_llm, extract_topic_strings

logger = setup_logger(__name__)

async def extract_topics(
    transcript: str,
    content_type: Optional[str] = None,
    simple_format: bool = False
) -> List[Dict[str, Any]] | List[str]:
    """
    Identifies key topics in the transcript using an LLM.

    Args:
        transcript (str): The transcript text.
        content_type (str, optional): Type of content ("office_hours", "planetary_call", "jup_and_juice").
                                     Helps tailor extraction to content format.
        simple_format (bool): If True, returns a simple list of topic strings instead of
                             rich topic objects. Default is False.

    Returns:
        Union[List[Dict[str, Any]], List[str]]:
            - If simple_format=False: List of rich topic objects with metadata
            - If simple_format=True: List of topic strings only
            - Returns empty list if none are found or an error occurs.
    """
    logger.info("Extracting topics using LLM...")
    if not transcript:
        logger.warning("Transcript is empty, cannot extract topics.")
        return []

    try:
        # Extract rich topic data
        topics = await extract_topics_llm(transcript, content_type)

        if topics is None:
            # Error logged within extract_topics_llm
            return [] # Return empty list on failure

        logger.info(f"Successfully extracted {len(topics)} topics.")

        # Return either rich topic objects or simple strings based on parameter
        if simple_format:
            topic_strings = extract_topic_strings(topics)
            logger.debug(f"Converted to simple topic strings: {topic_strings}")
            return topic_strings
        else:
            return topics

    except Exception as e:
        # Catch potential exceptions from the async call itself
        logger.error(f"An unexpected error occurred during topic extraction: {e}", exc_info=True)
        return []