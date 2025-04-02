"""
Configuration settings for the HorizonSummaries application.
"""

import os
from pathlib import Path


class Config:
    # Project directories
    ROOT_DIR = Path(__file__).parent.parent
    DATA_DIR = os.path.join(ROOT_DIR, "data")
    PROMPTS_DIR = os.path.join(DATA_DIR, "prompts")
    RESOURCES_DIR = os.path.join(DATA_DIR, "resources")
    OUTPUT_DIR = os.path.join(DATA_DIR, "output")

    # Temporary directory for downloaded files
    TEMP_DIR = os.path.join(ROOT_DIR, ".tmp")

    # AI Models
    DEFAULT_MODEL = "gemini-1.5-pro-002"  # Default model to use
    LESSER_MODEL = "gemini-1.5-flash-002"  # Fallback model

    # FalAI Whisper settings
    MAX_AUDIO_SIZE_MB = 50  # Maximum audio size in MB before splitting

    # Jupiter Terms file
    JUPITER_TERMS_FILE = os.path.join(RESOURCES_DIR, "jupiter_terms.json")

    # Maximum token limits
    MAX_TRANSCRIPT_TOKENS = 100000  # Maximum tokens for transcript processing
    MAX_SUMMARY_TOKENS = 4000  # Maximum tokens for summary generation

    # Logging
    LOG_LEVEL = "INFO"
    LOG_FILE = os.path.join(ROOT_DIR, "horizon_summaries.log")

    # Create directories if they don't exist
    @classmethod
    def init(cls):
        """Initialize configuration by creating necessary directories."""
        os.makedirs(cls.TEMP_DIR, exist_ok=True)
        os.makedirs(cls.OUTPUT_DIR, exist_ok=True)
        os.makedirs(cls.PROMPTS_DIR, exist_ok=True)
        os.makedirs(cls.RESOURCES_DIR, exist_ok=True)