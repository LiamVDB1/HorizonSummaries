"""
Prompt templates for summarization tasks.
"""

import os
import logging
from typing import Dict

from src.config import Config
from src.utils.file_handling import read_file

logger = logging.getLogger("horizon_summaries")


def get_prompt_template(template_type: str) -> str:
    """
    Get a prompt template for summarization.

    Args:
        template_type (str): Type of template (e.g., 'office_hours', 'planetary_call')

    Returns:
        str: Prompt template
    """
    template_path = os.path.join(Config.PROMPTS_DIR, f"{template_type}.txt")

    try:
        # Try to load template from file
        template = read_file(template_path)
        logger.info(f"Loaded {template_type} template from {template_path}")
        return template

    except FileNotFoundError:
        # If not found, use default template
        logger.warning(f"Template file {template_path} not found, using default")

        # If template type not recognized, use a generic template
        logger.warning(f"Unknown template type: {template_type}, using generic template")
        return get_prompt_template("default")


def list_available_templates() -> Dict[str, str]:
    """
    List all available templates with their descriptions.

    Returns:
        Dict[str, str]: Dictionary of template name -> description
    """
    templates = {}

    prompts_dir = Config.PROMPTS_DIR
    if os.path.exists(prompts_dir):
        for filename in os.listdir(prompts_dir):
            if filename.endswith('.txt'):
                template_name = os.path.splitext(filename)[0]
                templates[template_name] = f"Template: {template_name}"

    return templates