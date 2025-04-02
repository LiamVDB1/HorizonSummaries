#!/usr/bin/env python3
"""
HorizonSummaries - Main Execution Script

This script orchestrates the entire pipeline:
1. Downloads video from URL
2. Transcribes the audio to text
3. Preprocesses the transcript
4. Generates a summary using an AI model
5. Saves the results to files
"""

import os
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv

from src.config import Config
from src.utils.logger import setup_logger
from src.utils.file_handling import save_to_file, ensure_directory
from src.downloaders.common import identify_source, download_audio
from src.transcription.fal_whisper import transcribe_audio
from src.preprocessing.transcript_cleaner import clean_transcript
from src.preprocessing.term_correction import correct_jupiter_terms
from src.preprocessing.topic_extraction import extract_topics
from src.summarization.templates import get_prompt_template
from src.summarization.vertex_ai import generate_summary

# Load environment variables
load_dotenv()

# Setup logging
logger = setup_logger("horizon_summaries")


async def process_video(video_url: str, prompt_type: str, model_name: str = None):
    """
    Process a video URL through the entire pipeline.

    Args:
        video_url (str): The URL to the video to process
        prompt_type (str): Type of prompt to use (e.g., 'office_hours', 'planetary_call')
        model_name (str, optional): The AI model to use. Defaults to Config.DEFAULT_MODEL.

    Returns:
        str: Path to the generated summary file
    """
    try:
        # Create timestamp for file naming
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Identify the source type (youtube, twitter, etc.)
        source_type = identify_source(video_url)
        logger.info(f"Identified source as: {source_type}")

        # Download the audio file
        logger.info(f"Downloading audio from {video_url}")
        audio_path, video_title = download_audio(video_url)
        logger.info(f"Audio downloaded to {audio_path}")

        # Create base filename for outputs
        base_filename = f"{timestamp}_{video_title}"

        # Transcribe the audio
        logger.info("Transcribing audio...")
        transcript = transcribe_audio(audio_path)

        # Save raw transcript
        transcript_path = os.path.join(Config.OUTPUT_DIR, f"{base_filename}_transcript_raw.txt")
        save_to_file(transcript, transcript_path)
        logger.info(f"Raw transcript saved to {transcript_path}")

        # Clean and preprocess the transcript
        logger.info("Cleaning and preprocessing transcript...")
        cleaned_transcript = clean_transcript(transcript)
        corrected_transcript = correct_jupiter_terms(cleaned_transcript)

        # Extract topics from transcript
        topics = extract_topics(corrected_transcript)
        logger.info(f"Extracted topics: {', '.join(topics)}")

        # Save processed transcript
        processed_transcript_path = os.path.join(Config.OUTPUT_DIR, f"{base_filename}_transcript_processed.txt")
        save_to_file(corrected_transcript, processed_transcript_path)
        logger.info(f"Processed transcript saved to {processed_transcript_path}")

        # Get the prompt template
        prompt_template = get_prompt_template(prompt_type)

        # Generate summary
        logger.info(f"Generating summary using {model_name or Config.DEFAULT_MODEL}...")
        summary = await generate_summary(
            corrected_transcript,
            prompt_template,
            topics=topics,
            model_name=model_name or Config.DEFAULT_MODEL
        )

        # Save summary
        summary_path = os.path.join(Config.OUTPUT_DIR, f"{base_filename}_summary.md")
        save_to_file(summary, summary_path)
        logger.info(f"Summary saved to {summary_path}")

        # Cleanup temporary files
        if os.path.exists(audio_path):
            os.remove(audio_path)
            logger.info(f"Cleaned up temporary audio file: {audio_path}")

        return summary_path

    except Exception as e:
        logger.error(f"Error in processing pipeline: {str(e)}", exc_info=True)
        raise


def main():
    """Main entry point for the script."""
    # Ensure output directory exists
    ensure_directory(Config.OUTPUT_DIR)

    # Configure these variables for each run
    video_url = "https://youtube.com/watch?v=your_video_id"  # Replace with your video URL
    prompt_type = "office_hours"  # Options: 'office_hours', 'planetary_call', 'jup_and_juice'
    model_name = None  # Will use default from Config if None

    # Run the async process
    try:
        summary_path = asyncio.run(process_video(video_url, prompt_type, model_name))
        print(f"\n✅ Summary successfully generated and saved to: {summary_path}")
    except Exception as e:
        print(f"\n❌ Processing failed: {str(e)}")


if __name__ == "__main__":
    main()