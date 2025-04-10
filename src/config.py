# src/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables at module import time, BEFORE class definition
project_root = Path(__file__).parent.parent
dotenv_path = project_root / '.env'
load_dotenv(dotenv_path=dotenv_path)

class Config:
    """Stores configuration settings for the application."""

    # --- Project Root ---
    # Assumes config.py is in src/ directory
    PROJECT_ROOT = Path(__file__).parent.parent

    # --- Directories ---
    DATA_DIR = PROJECT_ROOT / "data"
    OUTPUT_DIR = DATA_DIR / "output"
    PROMPTS_DIR = DATA_DIR / "prompts"
    RESOURCES_DIR = DATA_DIR / "resources"
    DATABASE_DIR = DATA_DIR / "database" # New directory for the database

    HIGH_CONFIDENCE_THRESHOLD = 0.75  # Apply before LLM analysis
    MEDIUM_CONFIDENCE_THRESHOLD = 0.6  # Apply after LLM analysis if not conflicting

    # --- Files ---
    JUPITER_TERMS_FILE = RESOURCES_DIR / "jupiter_terms.json" # Path to known terms
    JUPITER_PEOPLE_FILE = RESOURCES_DIR / "jupiter_people.json"  # Path to known names
    TERM_DATABASE_FILE = DATABASE_DIR / "term_corrections.db" # Path to SQLite DB

    # --- API Credentials (Loaded from .env) ---
    FALAI_TOKEN = os.getenv("FALAI_TOKEN")
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    GOOGLE_PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID")
    GOOGLE_REGION = os.getenv("GOOGLE_REGION", "us-central1") # Default region

    # --- AI Model Settings ---
    # Default model for summarization, term analysis, topic extraction
    # Ensure this model supports function calling or structured JSON output if needed
    DEFAULT_MODEL = "gemini-2.5-pro-exp-03-25"
    LESSER_MODEL = "gemini-2.0-flash-001"

    # You might want separate models or configurations for different tasks
    TERM_ANALYSIS_MODEL = LESSER_MODEL
    TOPIC_EXTRACTION_MODEL = LESSER_MODEL
    SUMMARIZATION_MODEL = DEFAULT_MODEL

    # --- Transcription Settings ---
    FALAI_WHISPER_MODEL = "wizper"
    MAX_AUDIO_SIZE_MB = 50

    # --- Downloader Settings ---
    YT_DLP_FORMAT = "bestaudio/best"
    YT_DLP_OUTPUT_TEMPLATE = str(OUTPUT_DIR / "%(title)s_%(id)s.%(ext)s") # Temporary audio file path

    # --- Preprocessing Settings ---
    # Minimum confidence score for an LLM-suggested term correction to be added to the DB
    MIN_TERM_CORRECTION_CONFIDENCE = 0.8 # Example threshold (adjust as needed)

    # --- Logging ---
    #LOG_LEVEL = "INFO"
    LOG_LEVEL = "DEBUG"
    LOG_FILE = os.path.join(PROJECT_ROOT, "horizon_summaries.log")

    # --- Error Handling ---
    MAX_RETRIES = 3
    RETRY_DELAY = 5 # seconds

    @classmethod
    def validate(cls):
        """Validate essential configuration settings."""
        if not cls.FALAI_TOKEN:
            raise ValueError("FALAI_TOKEN environment variable not set.")
        if not cls.GOOGLE_APPLICATION_CREDENTIALS:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set.")
        if not cls.GOOGLE_PROJECT_ID:
            raise ValueError("GOOGLE_PROJECT_ID environment variable not set.")
        if not os.path.exists(cls.GOOGLE_APPLICATION_CREDENTIALS):
             raise FileNotFoundError(f"Google credentials file not found at: {cls.GOOGLE_APPLICATION_CREDENTIALS}")
        # Add more checks as needed

# Ensure directories exist when the config is loaded
Config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
Config.DATABASE_DIR.mkdir(parents=True, exist_ok=True)
Config.RESOURCES_DIR.mkdir(parents=True, exist_ok=True)

