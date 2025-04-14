"""
Handles generation of summaries using AI models.
"""

import logging
from typing import List, Dict, Any, Optional, Union

from src.config import Config
from src.preprocessing.reference_data import load_term_context, load_people_context, format_terms_for_prompt, format_people_for_prompt
from src.utils.logger import setup_logger
from src.llm.vertex_ai import VertexAIGenerator

logger = setup_logger(__name__)

def format_topics(topics: Optional[Union[List[str], List[Dict[str, Any]]]]) -> str:
    """
    Formats topics for inclusion in a summary prompt.

    Args:
        topics: List of topics as strings or rich topic objects

    Returns:
        Formatted topics string ready for template insertion
    """
    if not topics:
        return "No specific topics extracted"

    # Handle simple string list case
    if topics and isinstance(topics[0], str):
        return ", ".join(topics)

    # Handle rich topic objects with metadata
    if topics and isinstance(topics[0], dict):
        topics_formatted = "\n\n**Key Topics:**\n"
        for topic in topics:
            relevance = topic.get('relevance', 'medium')
            confidence = topic.get('confidence', 0.7)
            # Only include high and medium relevance topics with decent confidence
            if relevance in ['high', 'medium'] and confidence >= 0.7:
                topics_formatted += f"\n### {topic['topic']}\n"

                # Add key points if available
                if 'key_points' in topic and topic['key_points']:
                    topics_formatted += "Key points:\n"
                    for point in topic['key_points']:
                        topics_formatted += f"- {point}\n"

                # Add category if available
                if 'category' in topic and topic['category']:
                    topics_formatted += f"Category: {topic['category']}\n"

        return topics_formatted

    # Fallback for unexpected input
    return str(topics)


def prepare_summary_prompt(
        template: str,
        transcript: str,
        topics: Optional[Union[List[str], List[Dict[str, Any]]]] = None,
        term_data: Optional[Dict[str, Any]] = None,
        people_data: Optional[Dict[str, Any]] = None
) -> str:
    """Prepares a summary prompt with transcript, topics, and reference data."""
    topics_formatted = format_topics(topics)

    # Add reference data formatting
    terms_context = ""
    people_context = ""

    if term_data and "terms" in term_data:
        term_data["terms"]  = term_data["terms"][:35]  # Limit to most important
        terms_context = format_terms_for_prompt(term_data)

    if people_data and "people" in people_data:
        people_context = format_people_for_prompt(people_data) # Every person is important

    # Add to prompt
    context = f"{terms_context}{people_context}"

    # Format prompt with all components
    if "{TRANSCRIPT}" in template:
        # Support original uppercase format
        prompt = template.replace("{TRANSCRIPT}", transcript)
        prompt = prompt.replace("{TOPICS}", topics_formatted)
        prompt = prompt.replace("{JUPITER_CONTEXT}", context)  # Add placeholder in templates
    else:
        # Support newer lowercase format
        prompt = template.format(
            transcript=transcript,
            topics=topics_formatted,
            jupiter_context=context
        )

    return prompt

async def generate_summary(
    transcript: str,
    prompt_template: str,
    topics: Optional[Union[List[str], List[Dict[str, Any]]]] = None,
    model_name: str = Config.SUMMARIZATION_MODEL,
    temperature: float = 0.7,
    top_p: float = None,
    max_output_tokens: int = 8192,
    frequency_penalty: float = None,
) -> str:
    """
    Generate a summary using VertexAI.

    Args:
        transcript (str): The transcript to summarize
        prompt_template (str): Template for the prompt
        topics: Optional list of topics extracted from the transcript
        model_name (str): Model name to use
        temperature (float): Controls randomness in generation
        top_p (float): Nucleus sampling parameter
        max_output_tokens (int): Maximum tokens in the output
        frequency_penalty (float): Penalty for repeating tokens

    Returns:
        str: Generated summary
    """
    logger.info(f"Generating summary with model {model_name}")

    # Load Reference Data
    term_data = load_term_context()
    people_data = load_people_context()

    # Prepare the complete prompt
    prompt = prepare_summary_prompt(prompt_template, transcript, topics, term_data, people_data)

    # Initialize the generator
    generator = VertexAIGenerator()

    # Define a system instruction specific to summarization
    system_instruction = """You are an expert summarizer specializing in blockchain and crypto project communications, particularly for the Jupiter ecosystem on Solana. Your goal is to create clear, concise, and engaging summaries from transcripts.
    IMPORTANT: Be extremely precise with Jupiter-specific terminology and people names. If a name or term appears in the provided context lists, always use that exact spelling and capitalization.
    Focus on key decisions, announcements, technical details, community sentiment, and action items. Use Markdown formatting for readability."""

    logger.info("Sending summarization request to VertexAI")
    response = await generator.generate_response_with_retry(
        prompt=prompt,
        model= model_name,
        temperature=temperature,
        top_p=top_p,
        max_output_tokens=max_output_tokens,
        frequency_penalty=frequency_penalty,
        system_instruction=system_instruction
    )

    summary = response["content"]

    # Log token usage
    metadata = response["metadata"]
    logger.info(f"Summary generated with {metadata['total_token_count']} tokens, ({metadata['prompt_token_count']} prompt, {metadata['candidates_token_count']} response)")

    return summary

async def generate_topic_based_summary(
    transcript: str,
    prompt_template: str,
    topics: List[Dict[str, Any]],
    model_name: str = Config.SUMMARIZATION_MODEL,
) -> Dict[str, Any]:
    """
    Generate a comprehensive summary with separate sections for each major topic.

    Args:
        transcript: The transcript to summarize
        prompt_template: Base template for the prompt
        topics: List of rich topic objects with metadata
        model_name: Model name to use

    Returns:
        Dictionary containing the complete summary and section summaries
    """
    # First generate an overall summary
    full_summary = await generate_summary(transcript, prompt_template, topics, model_name)

    # Then generate mini-summaries for each high-relevance topic
    topic_summaries = {}
    for topic in topics:
        if not isinstance(topic, dict):
            continue

        topic_name = topic.get('topic', topic.get('name', ''))
        relevance = topic.get('relevance', 'medium')

        # Only generate detailed summaries for high-relevance topics
        if relevance == 'high' and topic_name:
            # Create a topic-specific prompt
            topic_prompt = f"""
            Focus specifically on the topic "{topic_name}" in this transcript. 
            Provide a concise 2-3 paragraph summary about this topic only.
            Include key points, decisions, or announcements related to this topic.
            
            Transcript:
            {transcript}
            """

            # Generate the topic-specific summary
            generator = VertexAIGenerator()
            response = await generator.generate_response_with_retry(
                prompt=topic_prompt,
                temperature=0.5,  # Lower temperature for more focused summary
                max_output_tokens=1000,
            )

            topic_summaries[topic_name] = response["content"]

    return {
        "full_summary": full_summary,
        "topic_summaries": topic_summaries
    }