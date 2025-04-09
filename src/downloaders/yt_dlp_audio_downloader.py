# src/downloaders/yt_dlp_audio_downloader.py
"""
Universal audio downloader using the yt-dlp Python API.
Handles all supported platforms (YouTube, Twitter, direct M3U8, etc.)
"""

import os
import tempfile
import logging
from typing import Tuple, Optional
from datetime import datetime
from pathlib import Path
import shutil

import yt_dlp

from src.config import Config
from src.utils.logger import setup_logger
from src.utils.file_handling import sanitize_filename

logger = setup_logger(__name__)


def download_audio(url: str, source_type: str = "generic") -> Tuple[Optional[str], Optional[str]]:
    """
    Downloads audio from any URL supported by yt-dlp.

    Args:
        url (str): The URL to download from.
        source_type (str): Identifier for the source type (youtube, twitter_broadcast, m3u8, etc.)
                          Used for naming the output file.

    Returns:
        Tuple[Optional[str], Optional[str]]: Path to the downloaded audio file and the title,
                                            or (None, None) on failure.
    """
    logger.info(f"Downloading audio from {source_type} URL: {url}")

    # Create a temporary file for the download
    with tempfile.NamedTemporaryFile(delete=False, suffix=".temp") as temp_file:
        temp_path = temp_file.name

    try:
        # Configure yt-dlp options
        ydl_opts = {
            'format': Config.YT_DLP_FORMAT,
            'outtmpl': f"{temp_path}.%(ext)s",
            'retries': 5,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
        }

        # Download and process
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info("Extracting information and downloading...")
            info_dict = ydl.extract_info(url, download=True)

            # Get video title
            video_title = info_dict.get('title', None)
            if not video_title:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                video_title = f"{source_type.capitalize()}_Content_{timestamp}"

            logger.info(f"Downloaded content with title: {video_title}")

            # Find the output file (should be temp_path.mp3 due to postprocessor)
            expected_output = f"{temp_path}.mp3"

            if os.path.exists(expected_output):
                # Create final path with clean filename
                sanitized_title = sanitize_filename(video_title)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                final_filename = f"{sanitized_title}_{source_type}_{timestamp}.mp3"
                final_path = os.path.join(str(Config.OUTPUT_DIR), final_filename)

                # Ensure output directory exists
                os.makedirs(os.path.dirname(final_path), exist_ok=True)

                # Move the file
                shutil.copy2(expected_output, final_path)
                logger.info(f"Successfully downloaded audio to: {final_path}")

                # Clean up
                os.remove(expected_output)
                if os.path.exists(temp_path):
                    os.remove(temp_path)

                return final_path, video_title
            else:
                logger.error(f"Expected output file not found: {expected_output}")
                return None, video_title

    except yt_dlp.utils.DownloadError as e:
        logger.error(f"yt-dlp download error for {source_type} URL {url}: {str(e)}")
        return None, None
    except Exception as e:
        logger.error(f"Unexpected error downloading from {source_type} URL {url}: {e}", exc_info=True)
        return None, None
    finally:
        # Clean up temporary files
        if os.path.exists(temp_path):
            os.remove(temp_path)
        for ext in ['.mp3', '.m4a', '.webm', '.temp']:
            temp_file_with_ext = f"{temp_path}{ext}"
            if os.path.exists(temp_file_with_ext):
                os.remove(temp_file_with_ext)