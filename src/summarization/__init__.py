"""
Text summarization with AI capabilities.
"""

from src.summarization.vertex_ai import generate_summary, VertexAIGenerator
from src.summarization.templates import get_prompt_template, list_available_templates

__all__ = [
    'generate_summary',
    'VertexAIGenerator',
    'get_prompt_template',
    'list_available_templates'
]