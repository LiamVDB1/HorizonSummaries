#!/usr/bin/env python3
"""
HorizonSummaries - Main Execution Script (Refactored)

Orchestrates the pipeline: Download -> Transcribe -> Clean -> Correct Terms (AI) -> Extract Topics (AI) -> Summarize (AI) -> Save.
"""

import os
import asyncio
import logging
import sys
from datetime import datetime
from dotenv import load_dotenv

# --- Load .env file before importing modules that use Config ---
# Determine the root directory (assuming main.py is in the project root)
project_root = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(project_root, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    print(f"Loaded environment variables from: {dotenv_path}")
else:
    print(f"Warning: .env file not found at {dotenv_path}. Proceeding with environment variables if set.")

# --- Add src to Python path ---
# This allows importing modules from src (e.g., from src.config import Config)
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)
    print(f"Added '{src_path}' to sys.path")


# --- Now import project modules ---
try:
    from src.config import Config
    from src.utils.logger import setup_logger
    from src.utils.file_handling import save_to_file, ensure_directory, sanitize_filename
    from src.database.term_db import initialize_database as init_term_db # Alias for clarity
    from src.llm.vertex_ai import initialize_vertex_ai as init_vertex # Alias
    from src.downloaders.common import download_audio # Identify source is internal now
    from src.transcription.fal_whisper import transcribe_audio
    from src.preprocessing.transcript_cleaner import clean_transcript
    from src.preprocessing.term_correction import correct_jupiter_terms # Refactored (async)
    from src.preprocessing.topic_extraction import extract_topics # Refactored (async)
    from src.summarization.templates import get_prompt_template
    from src.llm.vertex_ai import generate_summary # Moved (async)
except ImportError as e:
     print(f"Error importing project modules: {e}")
     print("Ensure you are running this script from the project root directory where main.py is located,")
     print("and that the 'src' directory is present and contains the necessary modules.")
     print(f"Current sys.path: {sys.path}")
     sys.exit(1)


# --- Setup Logging ---
# Note: setup_logger is called within modules, but configure root logger here if needed
logging.basicConfig(level=Config.LOG_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = setup_logger("horizon_summaries_main") # Logger for this main script


async def process_video(video_url: str, prompt_type: str, model_name: str = None):
    """
    Process a video URL through the entire pipeline (async).

    Args:
        video_url (str): The URL to the video to process.
        prompt_type (str): Type of prompt to use (e.g., 'office_hours', 'planetary_call').
        model_name (str, optional): Overrides the default AI model for summarization.

    Returns:
        str: Path to the generated summary file.

    Raises:
        Exception: If any critical step in the pipeline fails.
    """
    # --- Initialization ---
    # Ensure necessary services/databases are initialized before processing
    # These functions are designed to run safely multiple times if needed.
    logger.info("--- Starting Video Processing Pipeline ---")
    try:
        init_term_db()      # Ensure database table exists
        init_vertex()       # Initialize Vertex AI client
        Config.validate()   # Validate essential config from .env
    except Exception as init_error:
        logger.error(f"Initialization failed: {init_error}", exc_info=True)
        raise ValueError(f"Initialization failed: {init_error}") from init_error


    # --- Pipeline Steps ---
    audio_path = None # Ensure audio_path is defined for cleanup
    try:
        # Create timestamp for file naming
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 1. Download Audio (Handles source identification internally)
        logger.info(f"Attempting to download audio from: {video_url}")
        audio_path, video_title = download_audio(video_url)
        if not audio_path or not os.path.exists(audio_path):
            raise RuntimeError(f"Failed to download audio from {video_url}")
        if not video_title:
            video_title = f"Unknown_Video_{timestamp}"
            logger.warning("Could not retrieve video title, using generic name.")
        logger.info(f"Audio downloaded successfully to: {audio_path}")
        logger.info(f"Video Title: {video_title}")

        # Create base filename using sanitized title
        safe_title = sanitize_filename(video_title)
        base_filename = f"{timestamp}_{safe_title}"
        output_dir = Config.OUTPUT_DIR

        # 2. Transcribe Audio
        logger.info("Transcribing audio using FalAI Whisper...")
        transcript = transcribe_audio(audio_path, model=Config.FALAI_WHISPER_MODEL)
        if not transcript:
            raise RuntimeError("Transcription failed or returned empty.")
        logger.info("Transcription completed.")

        # Save raw transcript
        raw_transcript_path = output_dir / f"{base_filename}_transcript_raw.txt"
        save_to_file(transcript, raw_transcript_path)
        logger.info(f"Raw transcript saved to {raw_transcript_path}")

        # 3. Clean Transcript (Basic Cleaning)
        logger.info("Cleaning transcript (basic)...")
        cleaned_transcript = clean_transcript(transcript)
        logger.info("Basic cleaning finished.")

        # 4. Correct Jupiter Terms (AI-Powered + DB) - Async
        logger.info("Applying Jupiter term corrections (AI + DB)...")
        # This now involves an async LLM call internally
        corrected_transcript = await correct_jupiter_terms(cleaned_transcript)
        logger.info("Term correction finished.")

        # 5. Extract Topics (AI-Powered) - Async
        logger.info("Extracting topics using AI...")
        # This also involves an async LLM call
        topics = await extract_topics(corrected_transcript)
        if topics:
            logger.info(f"Extracted topics: {', '.join(topics)}")
        else:
            logger.warning("No topics were extracted.")

        # Save processed transcript (after cleaning and term correction)
        processed_transcript_path = output_dir / f"{base_filename}_transcript_processed.txt"
        save_to_file(corrected_transcript, processed_transcript_path)
        logger.info(f"Processed transcript saved to {processed_transcript_path}")

        # 6. Generate Summary (AI-Powered) - Async
        logger.info("Generating summary using AI...")
        prompt_template = get_prompt_template(prompt_type)
        if not prompt_template:
            raise ValueError(f"Prompt template '{prompt_type}' not found.")

        summary_model = model_name or Config.SUMMARIZATION_MODEL
        logger.info(f"Using summarization model: {summary_model}")
        summary = await generate_summary(
            transcript=corrected_transcript, # Use the term-corrected transcript
            prompt_template=prompt_template,
            topics=topics,
            model_name=summary_model
        )
        if not summary:
             raise RuntimeError("Summary generation failed or returned empty.")
        logger.info("Summary generation completed.")

        # 7. Save Summary
        summary_path = output_dir / f"{base_filename}_summary.md"
        save_to_file(summary, summary_path)
        logger.info(f"Summary saved to {summary_path}")

        logger.info("--- Video Processing Pipeline Completed Successfully ---")
        return str(summary_path) # Return path as string

    except Exception as e:
        logger.error(f"Error in processing pipeline for URL {video_url}: {str(e)}", exc_info=True)
        # Log specific details if available (e.g., which step failed)
        # Re-raise the exception to be caught by the main function's handler
        raise
    finally:
        # 8. Cleanup Temporary Files
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
                logger.info(f"Cleaned up temporary audio file: {audio_path}")
            except OSError as rm_error:
                logger.warning(f"Could not remove temporary audio file {audio_path}: {rm_error}")
        else:
             logger.debug("No temporary audio file path found for cleanup.")


def main():
    """Main entry point for the script."""
    # Ensure output directory exists (Config handles this now, but double-check)
    ensure_directory(Config.OUTPUT_DIR)
    ensure_directory(Config.DATABASE_DIR) # Ensure DB dir exists too

    # --- Configuration for this run ---
    # Get from command-line arguments or environment variables for flexibility
    # Example using environment variables (or replace with argparse)
    video_url = os.getenv("VIDEO_URL")
    # Default URL if not set via environment variable
    if not video_url:
         # Use the placeholder from the original script if needed
         video_url = "[https://youtube.com/watch?v=your_video_id](https://youtube.com/watch?v=your_video_id)" # Replace with a REAL test URL
         logger.warning(f"VIDEO_URL environment variable not set. Using default/placeholder: {video_url}")
         # It's better to require the URL, e.g., via command-line arg

    prompt_type = os.getenv("PROMPT_TYPE", "office_hours") # Default prompt type
    # Options: 'office_hours', 'planetary_call', 'jup_and_juice', etc. (match files in data/prompts)

    model_name = os.getenv("MODEL_NAME", None) # Optional override for summarization model
    # If None, uses Config.SUMMARIZATION_MODEL

    # --- Validate Inputs ---
    if not video_url or video_url == "[https://youtube.com/watch?v=your_video_id](https://youtube.com/watch?v=your_video_id)":
        print("\n❌ Error: Please provide a valid video URL.")
        print("   Set the VIDEO_URL environment variable or modify the script.")
        sys.exit(1)
    if not get_prompt_template(prompt_type): # Check if prompt exists
         print(f"\n❌ Error: Prompt type '{prompt_type}' not found in {Config.PROMPT_DIR}.")
         # List available prompts
         try:
             available_prompts = [f.stem for f in Config.PROMPT_DIR.glob('*.txt')]
             print(f"   Available prompt types: {', '.join(available_prompts)}")
         except Exception:
             pass # Ignore if listing fails
         sys.exit(1)


    print("\n--- HorizonSummaries ---")
    print(f"Processing URL: {video_url}")
    print(f"Using Prompt Type: {prompt_type}")
    if model_name: print(f"Overriding Summary Model: {model_name}")
    print("------------------------")

    # --- Run the async processing pipeline ---
    try:
        # asyncio.run() executes the async function
        summary_path = asyncio.run(process_video(video_url, prompt_type, model_name))
        print(f"\n✅ Summary successfully generated and saved to: {summary_path}")
        print("------------------------\n")
    except Exception as e:
        # Errors are logged within process_video, just print final status
        print(f"\n❌ Processing failed. Check logs for details. Error: {str(e)}")
        print("------------------------\n")
        sys.exit(1) # Exit with error code


if __name__ == "__main__":
    # Example Usage (Set environment variables before running):
    # export VIDEO_URL="[https://www.youtube.com/watch?v=](https://www.youtube.com/watch?v=)..."
    # export PROMPT_TYPE="office_hours"
    # export FALAI_TOKEN="..."
    # export GOOGLE_APPLICATION_CREDENTIALS="..."
    # export GOOGLE_PROJECT_ID="..."
    # python main.py

    # Or modify the defaults in the main() function for testing.
    main()
