# src/llm/topic_extractor.py
"""
Uses Vertex AI to extract key topics and related information from transcripts.
"""

import logging
import json
from typing import List, Dict, Optional, Any, Union

from src.config import Config
from src.llm.vertex_ai import VertexAIGenerator
from src.utils.logger import setup_logger
from src.utils.json_parser import parse_json_from_llm

logger = setup_logger(__name__)

async def extract_topics_llm(
        transcript: str,
        content_type: Optional[str] = None,
        model_name: str = Config.TOPIC_EXTRACTION_MODEL,
        max_topics: int = 10  # Limit the number of topics
) -> Optional[List[Dict[str, Any]]]:
    """
    Extracts key topics and related information from a transcript using an LLM.

    Args:
        transcript (str): The transcript text to analyze.
        content_type (str, optional): Type of content ("office_hours", "planetary_call", "jup_and_juice").
                                     Helps tailor the extraction to specific content formats.
        model_name (str): The Vertex AI model to use.
        max_topics (int): Approximate maximum number of topics to return.

    Returns:
        Optional[List[Dict[str, Any]]]: A list of topic objects with metadata,
                                       or None if extraction fails.
    """
    if not transcript:
        logger.warning("Transcript is empty, skipping topic extraction.")
        return None

    logger.info(f"Starting topic extraction with model: {model_name}")

    # Base prompt with enhanced structure
    prompt = f"""
Analyze the following transcript from a Jupiter DAO communication and identify the main topics discussed.

**Transcript:**
```
{transcript}
```

**Instructions:**
1. Read the transcript carefully to understand the key subjects, themes, and announcements.
2. Identify the most important topics covered, focusing on specific subjects, projects, announcements, or discussions.
3. For each topic:
   - Create a concise topic label (1-5 words)
   - Identify 1-3 key points that summarize what was discussed about this topic
   - Assess the relevance/importance (high, medium, low) based on discussion time and emphasis
   - Suggest an appropriate category for the topic (e.g., "Governance", "Development", "Community", "Tokenomics", etc.)
   - Include a confidence score (0.0-1.0) indicating your certainty about this topic's presence
4. Return ONLY a valid JSON array of objects in the format shown in the example below.
5. Aim for approximately {max_topics} topics, but adjust based on the content's density.
6. Focus on extracting specific, actionable information rather than general themes.
7. If the transcript is too short or lacks clear topics, return an empty JSON array.

**Example Output Format:**
```json
[
  {{
    "topic": "LFG Launchpad Updates",
    "key_points": [
      "Three new projects were voted into the launchpad",
      "Application process is being streamlined",
      "New monitoring system launching next week"
    ],
    "relevance": "high",
    "category": "Governance",
    "confidence": 0.95
  }},
  {{
    "topic": "Perpetual Futures Market",
    "key_points": [
      "Trading volume increased by 30% last week",
      "New UI improvements coming soon"
    ],
    "relevance": "medium",
    "category": "Product",
    "confidence": 0.88
  }}
]
```
"""

    # Add content-type specific guidance if provided
    if content_type:
        if content_type.lower() == "office_hours":
            prompt += """
**Office Hours Context:**
For Jupiter Office Hours, pay special attention to:
- Working group updates and responsibilities
- Community initiatives and contributions
- DAO governance proposals and votes
- Project timelines and milestones
"""
        elif content_type.lower() == "planetary_call":
            prompt += """
**Planetary Call Context:**
For Jupiter Planetary Calls, focus on:
- Technical announcements and product launches
- Development roadmap and timelines
- Strategic decisions and partnerships
- Community governance and proposals
"""
        elif content_type.lower() == "jup_and_juice":
            prompt += """
**Jup & Juice Context:**
For Jup & Juice podcasts, emphasize:
- Guest introductions and backgrounds
- Interview themes and talking points
- Jupiter ecosystem discussions
- Industry trends and observations
"""

    # Add Jupiter-specific context
    prompt += """
**Jupiter-Specific Context:**
- Topics may relate to Jupiter Swap, Perps, Limit Orders, Liquidity, or DAO governance
- Working groups include Core (CWG), Uplink, Jup & Juice, Catdet (CAWG), Devrel (DRWG), Design (DAWG)
- Ecosystem projects often include collaborations with other Solana protocols

**JSON Response:**
"""

    # System instruction for topic extraction
    system_instruction = """You are an AI assistant skilled at identifying key topics within lengthy text documents, specifically transcripts related to Jupiter DAO communications. Your goal is to extract a structured list of the most relevant subjects discussed with supporting information. Output must be a valid JSON array of topic objects."""

    try:
        generator = VertexAIGenerator()

        llm_output = await generator.generate_response_with_retry(
            prompt=prompt,
            model=model_name,
            temperature=0.3,  # Moderate temperature for topic identification
            max_output_tokens=2048,  # Increased for more detailed responses
            system_instruction=system_instruction
        )

        raw_llm_output = llm_output.get("content", "")

        if not raw_llm_output:
            logger.warning("Topic extraction LLM returned an empty response.")
            return None

        # Parse the JSON response
        topics = parse_json_from_llm(raw_llm_output, description="topic extraction")

        if topics is None:
            logger.error("Failed to parse JSON topics from LLM response.")
            return None

        if not isinstance(topics, list):
            logger.error(f"Topic extraction LLM response was not a valid list: {topics}")
            return None

        # Validate the structure of each topic
        valid_topics = []
        for topic_data in topics:
            if not isinstance(topic_data, dict):
                logger.warning(f"Invalid topic data format (not a dict): {topic_data}")
                continue

            # Ensure required fields
            if 'topic' not in topic_data:
                logger.warning(f"Missing 'topic' field in: {topic_data}")
                continue

            # Ensure key_points is a list if present
            if 'key_points' in topic_data and not isinstance(topic_data['key_points'], list):
                topic_data['key_points'] = [topic_data['key_points']]

            # Add default values for optional fields if missing
            if 'relevance' not in topic_data:
                topic_data['relevance'] = 'medium'

            if 'confidence' not in topic_data:
                topic_data['confidence'] = 0.7

            valid_topics.append(topic_data)

        logger.info(f"Topic extraction identified {len(valid_topics)} topics.")
        logger.debug(f"Extracted topics: {valid_topics}")
        return valid_topics

    except Exception as e:
        logger.error(f"Error during topic extraction LLM call: {e}", exc_info=True)
        return None


def extract_topic_strings(topic_data: List[Dict[str, Any]]) -> List[str]:
    """
    Extracts just the topic strings from the structured topic data.
    Useful for backward compatibility with code expecting just topic strings.

    Args:
        topic_data (List[Dict[str, Any]]): List of topic objects with metadata

    Returns:
        List[str]: List of topic strings
    """
    if not topic_data:
        return []

    return [item.get('topic', '') for item in topic_data if item.get('topic')]