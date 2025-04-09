#!/usr/bin/env python3
"""
HorizonSummaries - Main Execution Script (Direct Variable Assignment)

Orchestrates the pipeline: Download -> Transcribe -> Clean -> Correct Terms (AI) -> Extract Topics (AI) -> Summarize (AI) -> Save.
Set video URL and prompt type directly in the __main__ block before running.
"""

import os
import asyncio
import logging
import sys
# No argparse needed anymore
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# --- Load .env file ---
project_root = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(project_root, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    print(f"Loaded environment variables from: {dotenv_path}")
else:
    print(f"Warning: .env file not found at {dotenv_path}. Ensure API keys are set via environment variables.")

# --- Add src to Python path ---
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)
    print(f"Added '{src_path}' to sys.path")

# --- Imports ---
try:
    from src.config import Config
    from src.utils.logger import setup_logger
    from src.utils.file_handling import save_to_file, ensure_directory, sanitize_filename
    from src.database.term_db import initialize_database as init_term_db
    from src.llm.vertex_ai import initialize_vertex_ai as init_vertex
    from src.downloaders.common import download_audio
    from src.transcription.fal_whisper import transcribe_audio
    from src.preprocessing.transcript_cleaner import clean_transcript
    from src.preprocessing.term_correction import correct_jupiter_terms
    from src.preprocessing.topic_extraction import extract_topics
    from src.summarization.templates import get_prompt_template # We still need this
    from src.llm.vertex_ai import generate_summary
except ImportError as e:
     print(f"Error importing project modules: {e}")
     print("Ensure you are running this script from the project root directory where main.py is located,")
     print("and that the 'src' directory is present and contains the necessary modules.")
     print(f"Current sys.path: {sys.path}")
     sys.exit(1)
except Exception as e:
    print(f"An unexpected error occurred during initial imports: {e}")
    sys.exit(1)

# --- Logging ---
logging.basicConfig(level=Config.LOG_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = setup_logger("horizon_summaries_main")


async def process_video(video_url: str, prompt_type: str, model_name: str = None):
    """
    Process a video URL through the entire pipeline (async).

    Args:
        video_url (str): The URL to the video to process.
        prompt_type (str): Type of prompt (string identifier like 'office_hours').
        model_name (str, optional): Overrides the default AI model for summarization.

    Returns:
        str: Path to the generated summary file.

    Raises:
        Exception: If any critical step in the pipeline fails.
    """
    # --- Initialization ---
    logger.info("--- Starting Video Processing Pipeline ---")
    try:
        init_term_db()
        init_vertex()
        Config.validate()
    except Exception as init_error:
        logger.error(f"Initialization failed: {init_error}", exc_info=True)
        raise ValueError(f"Initialization failed: {init_error}") from init_error

    # --- Pipeline Steps ---
    audio_path = None
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 1. Download Audio
        logger.info(f"Attempting to download audio from: {video_url}")
        audio_path, video_title = download_audio(video_url)
        if not audio_path or not os.path.exists(audio_path):
            raise RuntimeError(f"Failed to download audio from {video_url}")
        if not video_title:
            video_title = f"Unknown_Video_{timestamp}"
        logger.info(f"Audio downloaded successfully to: {audio_path}")
        logger.info(f"Video Title: {video_title}")

        safe_title = sanitize_filename(video_title)
        base_filename = f"{timestamp}_{safe_title}"
        output_dir = Config.OUTPUT_DIR

        # 2. Transcribe Audio
        logger.info("Transcribing audio...")
        transcript = transcribe_audio(audio_path, model=Config.FALAI_WHISPER_MODEL)
        if not transcript: raise RuntimeError("Transcription failed or returned empty.")
        logger.info("Transcription completed.")
        raw_transcript_path = output_dir / f"{base_filename}_transcript_raw.txt"
        save_to_file(transcript, raw_transcript_path)
        logger.info(f"Raw transcript saved to {raw_transcript_path}")

        # 3. Clean Transcript
        logger.info("Cleaning transcript...")
        cleaned_transcript = clean_transcript(transcript)
        logger.info("Basic cleaning finished.")

        # 4. Correct Jupiter Terms
        logger.info("Applying Jupiter term corrections...")
        corrected_transcript = await correct_jupiter_terms(cleaned_transcript)
        logger.info("Term correction finished.")

        # 5. Extract Topics
        logger.info("Extracting topics...")
        topics = await extract_topics(corrected_transcript)
        if topics: logger.info(f"Extracted topics: {', '.join(topics)}")
        else: logger.warning("No topics were extracted.")
        processed_transcript_path = output_dir / f"{base_filename}_transcript_processed.txt"
        save_to_file(corrected_transcript, processed_transcript_path)
        logger.info(f"Processed transcript saved to {processed_transcript_path}")

        # 6. Generate Summary
        logger.info("Generating summary...")
        prompt_template = get_prompt_template(prompt_type) # Fetch template using the string name
        if not prompt_template:
             # Even without argparse, we should check if the template exists
             logger.error(f"Prompt template '{prompt_type}' could not be loaded. Check data/prompts folder.")
             raise ValueError(f"Prompt template '{prompt_type}' not found.")

        summary_model = model_name or Config.SUMMARIZATION_MODEL
        logger.info(f"Using summarization model: {summary_model}")
        summary = await generate_summary(
            transcript=corrected_transcript,
            prompt_template=prompt_template,
            topics=topics,
            model_name=summary_model
        )
        if not summary: raise RuntimeError("Summary generation failed or returned empty.")
        logger.info("Summary generation completed.")

        # 7. Save Summary
        summary_path = output_dir / f"{base_filename}_summary.md"
        save_to_file(summary, summary_path)
        logger.info(f"Summary saved to {summary_path}")

        logger.info("--- Video Processing Pipeline Completed Successfully ---")
        return str(summary_path)

    except Exception as e:
        logger.error(f"Error in processing pipeline for URL {video_url}: {str(e)}", exc_info=True)
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


def main(video_url: str, prompt_type: str, model_name: str = None):
    """
    Main execution function: Initializes directories and runs the async pipeline.
    Now takes url, prompt_type, and model_name as arguments.
    """
    # Ensure output directories exist
    ensure_directory(Config.OUTPUT_DIR)
    ensure_directory(Config.DATABASE_DIR)

    print("\n--- HorizonSummaries ---")
    print(f"Processing URL: {video_url}")
    print(f"Using Prompt Type: {prompt_type}")
    if model_name: print(f"Overriding Summary Model: {model_name}")
    print("------------------------")

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
    # --- !!! EDIT THESE VARIABLES BEFORE RUNNING !!! ---
    video_url_to_process = "https://x.com/i/broadcasts/1OyKALnErRaxb"

    # Specify the prompt type (must match a filename in data/prompts without .txt)
    prompt_type_to_use = "office_hours"

    model_override = 'gemini-2.5-pro-exp-03-25'

    main(video_url=video_url_to_process,
         prompt_type=prompt_type_to_use,
         model_name=model_override)
