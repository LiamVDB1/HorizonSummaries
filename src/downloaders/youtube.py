# src/downloaders/youtube.py
"""
Handles downloading audio from YouTube URLs using yt-dlp.
"""

import logging
import subprocess
import re
import os
from typing import Tuple, Optional
from urllib.parse import urlparse

from src.config import Config
from src.utils.logger import setup_logger
# Assuming sanitize_filename is in file_handling or create it if needed
from src.utils.file_handling import sanitize_filename

logger = setup_logger(__name__)

def is_youtube_url(url: str) -> bool:
    """Checks if the URL is a valid YouTube URL."""
    parsed_url = urlparse(url)
    # Check for standard youtube.com domains (www, music, etc.) and youtu.be shortlinks
    return (parsed_url.netloc.endswith("youtube.com") or
            parsed_url.netloc == "youtu.be")

def download_youtube_audio(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Downloads audio from a YouTube URL using yt-dlp.

    Args:
        url (str): The URL of the YouTube video.

    Returns:
        Tuple[Optional[str], Optional[str]]: Path to the downloaded audio file and the video title,
                                             or (None, None) on failure.
    """
    if not is_youtube_url(url):
        logger.warning(f"URL '{url}' is not recognized as a YouTube URL. Skipping YouTube downloader.")
        return None, None # Should ideally not be called if common.py identifies correctly

    logger.info(f"Attempting to download audio for YouTube URL: {url}")

    # Define the output template specifically for YouTube downloads
    # Using pathlib for path construction
    output_template_path = Config.OUTPUT_DIR / "%(title)s_youtube_%(id)s.%(ext)s"
    output_template = str(output_template_path)

    final_audio_path = None
    video_title = None

    try:
        # 1. Get video title using yt-dlp
        info_command = [
            "yt-dlp",
            "--get-title",
            "--no-warnings",
            # Add any necessary cookies arguments if needed for private videos etc.
            # "--cookies-from-browser", "chrome",
            url
        ]
        logger.debug(f"Running yt-dlp command for title: {' '.join(info_command)}")
        title_process = subprocess.run(info_command, capture_output=True, text=True, check=True, encoding='utf-8')
        video_title = title_process.stdout.strip()
        logger.info(f"Extracted video title: {video_title}")

        # Sanitize title for filename construction (used for guessing path if needed)
        sanitized_title = sanitize_filename(video_title) if video_title else "youtube_video"
        expected_output_base = str(Config.OUTPUT_DIR / f"{sanitized_title}_youtube_")

        # 2. Download the best audio format specified in Config
        download_command = [
            "yt-dlp",
            "-f", Config.YT_DLP_FORMAT, # e.g., "bestaudio/best"
            "--no-warnings",
            "--output", output_template, # Let yt-dlp handle the exact naming
            # "--verbose", # Uncomment for debugging
            url
        ]
        logger.debug(f"Running yt-dlp command for download: {' '.join(download_command)}")
        download_process = subprocess.run(download_command, capture_output=True, text=True, check=True, encoding='utf-8')
        logger.info("yt-dlp YouTube download process completed.")
        logger.debug(f"yt-dlp stdout:\n{download_process.stdout}")
        logger.debug(f"yt-dlp stderr:\n{download_process.stderr}") # Check stderr for path info too

        # 3. Find the actual downloaded file path from yt-dlp's output
        output_lines = download_process.stdout.splitlines() + download_process.stderr.splitlines()
        # Common patterns indicating the final output file
        destination_pattern = re.compile(r"\[(?:download|ExtractAudio|Merger)\].*Destination: (.*)")
        # Alternative pattern sometimes seen with ffmpeg merging/conversion
        merger_pattern = re.compile(r"Merging formats into \"(.*)\"")
        deleting_intermediate_pattern = re.compile(r"Deleting original file (.*) \(pass -k to keep\)")


        actual_path_found = None
        potential_intermediate = None

        for line in output_lines:
            dest_match = destination_pattern.search(line)
            merger_match = merger_pattern.search(line)

            if dest_match:
                path = dest_match.group(1).strip()
                 # Check if it's likely the final audio file or an intermediate
                if path.lower().endswith(('.m4a', '.mp3', '.wav', '.ogg', '.aac', '.opus')):
                     actual_path_found = path
                     logger.info(f"Found potential destination: {actual_path_found}")
                     # Don't break immediately, Merger message is more definitive if present
                else:
                     potential_intermediate = path # Store potential intermediate path

            elif merger_match:
                 # This is usually the most reliable indicator of the final merged file
                 actual_path_found = merger_match.group(1).strip()
                 logger.info(f"Found final merged file destination: {actual_path_found}")
                 break # Found the definitive path

        # If Merger pattern wasn't found, use the last Destination match that looks like audio
        if actual_path_found:
             final_audio_path = actual_path_found
             logger.info(f"Successfully determined downloaded audio file: {final_audio_path}")
        else:
            # Fallback: Check if an intermediate file was deleted (often implies the other was kept)
            # This is less reliable
            logger.warning("Could not reliably determine the downloaded audio file path from yt-dlp output (Destination/Merger).")
            logger.warning("Attempting to guess based on expected pattern...")
            # Use the guessing logic similar to other downloaders
            import glob
            potential_files = glob.glob(expected_output_base + "*")
            audio_extensions = ('.m4a', '.mp3', '.wav', '.ogg', '.aac', '.opus', '.webm') # Include webm just in case
            audio_files = [f for f in potential_files if f.lower().endswith(audio_extensions)]
            if audio_files:
                 # Sort by modification time, newest first
                 audio_files.sort(key=os.path.getmtime, reverse=True)
                 final_audio_path = audio_files[0]
                 logger.warning(f"Guessed audio file path based on pattern: {final_audio_path}")
            else:
                 logger.error("Failed to find downloaded audio file even with pattern matching.")
                 # Return the title if we got it, but path is None
                 return None, video_title

        # Final check if path exists
        if final_audio_path and os.path.exists(final_audio_path):
             return final_audio_path, video_title
        else:
             logger.error(f"Determined path '{final_audio_path}' does not exist on disk.")
             return None, video_title


    except subprocess.CalledProcessError as e:
        logger.error(f"yt-dlp failed for YouTube URL {url}. Return code: {e.returncode}")
        # Log only relevant parts of stdout/stderr to avoid excessive length
        stderr_snippet = (e.stderr[:500] + '...') if e.stderr and len(e.stderr) > 500 else e.stderr
        stdout_snippet = (e.stdout[:500] + '...') if e.stdout and len(e.stdout) > 500 else e.stdout
        logger.error(f"yt-dlp stderr (snippet): {stderr_snippet}")
        logger.error(f"yt-dlp stdout (snippet): {stdout_snippet}")
        return None, video_title # Return title if extracted before failure
    except FileNotFoundError:
        logger.error("yt-dlp command not found. Make sure yt-dlp is installed and in your system's PATH.")
        # This is a critical setup error
        raise RuntimeError("yt-dlp not found. Please install it.") from None
    except Exception as e:
        logger.error(f"An unexpected error occurred during YouTube download for {url}: {e}", exc_info=True)
        return None, None # General failure

