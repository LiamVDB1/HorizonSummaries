# src/downloaders/twitter.py
"""
Handles downloading audio from Twitter (X) broadcast URLs.
Attempts to use yt-dlp directly first.
"""

import logging
import subprocess
import json
import re
from typing import Tuple, Optional
from urllib.parse import urlparse

# Consider adding yt-dlp as a direct dependency if not already managed
# import yt_dlp # Or use subprocess call

from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

def is_twitter_broadcast_url(url: str) -> bool:
    """Checks if the URL is a Twitter (X) broadcast URL."""
    parsed_url = urlparse(url)
    return (parsed_url.netloc in ["twitter.com", "x.com"] and
            parsed_url.path.startswith("/i/broadcasts/"))

def download_twitter_broadcast_audio(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Downloads audio from a Twitter broadcast URL using yt-dlp.

    Args:
        url (str): The URL of the Twitter broadcast (e.g., [https://x.com/i/broadcasts/](https://www.google.com/search?q=https://x.com/i/broadcasts/)...).

    Returns:
        Tuple[Optional[str], Optional[str]]: Path to the downloaded audio file and the video title,
                                             or (None, None) on failure.
    """
    logger.info(f"Attempting to download audio for Twitter broadcast: {url}")

    # Define the output template for yt-dlp. Use placeholders for title and ID.
    # Ensure the output directory exists (handled by Config)
    output_template = str(Config.OUTPUT_DIR / "%(title)s_twitter_%(id)s.%(ext)s")
    final_audio_path = None
    video_title = None

    # --- Attempt 1: Use yt-dlp directly ---
    # yt-dlp often handles these URLs directly, including finding the m3u8.
    try:
        # Command to get metadata (title) first
        info_command = [
            "yt-dlp",
            "--get-title",
            "--no-warnings",
            # "--cookies-from-browser", "chrome", # Optional: May help if login is required
            url
        ]
        logger.debug(f"Running yt-dlp command for title: {' '.join(info_command)}")
        title_process = subprocess.run(info_command, capture_output=True, text=True, check=True, encoding='utf-8')
        video_title = title_process.stdout.strip()
        logger.info(f"Extracted video title: {video_title}")

        # Sanitize title for filename (replace invalid characters)
        sanitized_title = re.sub(r'[\\/*?:"<>|]', "_", video_title) if video_title else "twitter_broadcast"
        # Construct final path based on actual title
        # Note: yt-dlp's template might differ slightly, we find the *actual* file later
        expected_output_base = str(Config.OUTPUT_DIR / f"{sanitized_title}_twitter_")


        # Command to download the best audio
        download_command = [
            "yt-dlp",
            "-f", Config.YT_DLP_FORMAT, # Format selection (bestaudio/best)
            "--no-warnings",
            "--output", output_template, # Let yt-dlp handle naming
            # "--verbose", # Uncomment for debugging yt-dlp issues
            # "--cookies-from-browser", "chrome", # May be needed
            url
        ]
        logger.debug(f"Running yt-dlp command for download: {' '.join(download_command)}")
        download_process = subprocess.run(download_command, capture_output=True, text=True, check=True, encoding='utf-8')
        logger.info("yt-dlp download process completed.")
        logger.debug(f"yt-dlp stdout:\n{download_process.stdout}")
        logger.debug(f"yt-dlp stderr:\n{download_process.stderr}") # Check stderr for download path info

        # --- Find the downloaded file ---
        # yt-dlp usually prints the final filename to stdout or stderr.
        # Let's search stdout first. A common pattern is "[download] Destination: ..."
        # Or sometimes "[ExtractAudio] Destination: ..."
        output_lines = download_process.stdout.splitlines() + download_process.stderr.splitlines()
        destination_pattern = re.compile(r"\[(?:download|ExtractAudio)\].*Destination: (.*)")
        actual_path_found = None
        for line in output_lines:
            match = destination_pattern.search(line)
            if match:
                actual_path_found = match.group(1).strip()
                # Ensure it's an audio file (common extensions)
                if actual_path_found.lower().endswith(('.m4a', '.mp3', '.wav', '.ogg', '.aac', '.opus', '.webm')):
                    final_audio_path = actual_path_found
                    logger.info(f"Successfully downloaded audio file: {final_audio_path}")
                    break # Found the audio file path

        if not final_audio_path:
             logger.warning("Could not reliably determine the downloaded audio file path from yt-dlp output. Attempting to guess based on pattern...")
             # Fallback: Guess based on the expected pattern (less reliable)
             # List files matching the pattern and pick the most recent? Or assume only one matches?
             import glob
             potential_files = glob.glob(expected_output_base + "*")
             audio_extensions = ('.m4a', '.mp3', '.wav', '.ogg', '.aac', '.opus', '.webm')
             audio_files = [f for f in potential_files if f.lower().endswith(audio_extensions)]
             if audio_files:
                 # Sort by modification time if multiple matches? Assume latest is correct.
                 audio_files.sort(key=os.path.getmtime, reverse=True)
                 final_audio_path = audio_files[0]
                 logger.warning(f"Guessed audio file path: {final_audio_path}")
             else:
                 logger.error("Failed to find downloaded audio file even with pattern matching.")
                 return None, video_title # Return title even if download path failed

        return final_audio_path, video_title

    except subprocess.CalledProcessError as e:
        logger.error(f"yt-dlp failed for URL {url}. Return code: {e.returncode}")
        logger.error(f"yt-dlp stdout: {e.stdout}")
        logger.error(f"yt-dlp stderr: {e.stderr}")
        # --- Attempt 2: Manual m3u8 extraction (More complex, less reliable) ---
        # This would involve using `requests` to get the page, then parsing HTML/JS
        # to find the m3u8 URL, potentially mimicking browser network requests.
        # This is significantly more complex and prone to breaking if Twitter changes its site.
        # For now, we rely on yt-dlp. If direct calls consistently fail,
        # implementing manual extraction would be the next step, possibly using
        # libraries like `requests` and `beautifulsoup4` or even `playwright`.
        logger.error("Direct yt-dlp call failed. Manual m3u8 extraction is not yet implemented.")
        return None, None # Indicate failure
    except FileNotFoundError:
        logger.error("yt-dlp command not found. Make sure yt-dlp is installed and in your system's PATH.")
        return None, None
    except Exception as e:
        logger.error(f"An unexpected error occurred during Twitter download: {e}", exc_info=True)
        return None, None

