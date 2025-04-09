"""
AI/LLM services for Jupiter Horizon Summaries.
"""

from src.llm.vertex_ai import (
    initialize_vertex_ai,
    generate_text,
    generate_summary,
    parse_json_from_llm
)
from src.llm.term_analyzer import analyze_transcript_for_term_errors
from src.llm.topic_extractor import extract_topics_llm

# Initialize Vertex AI on module import to ensure it's ready when needed
initialize_vertex_ai()

__all__ = [
    "initialize_vertex_ai",
    "generate_text",
    "generate_summary",
    "parse_json_from_llm",
    "analyze_transcript_for_term_errors",
    "extract_topics_llm"
]