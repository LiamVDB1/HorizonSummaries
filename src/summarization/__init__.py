"""
Text summarization with AI capabilities.
"""

from src.summarization.summary_generator import generate_summary
from src.summarization.templates import get_prompt_template, list_available_templates

__all__ = [
    'generate_summary',
    'get_prompt_template',
    'list_available_templates'
]