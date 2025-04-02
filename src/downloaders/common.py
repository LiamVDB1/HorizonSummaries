# src/downloaders/common.py
"""
Common utilities for identifying video sources and orchestrating downloads.
"""

import logging
import subprocess
import re
import os
from typing import Tuple, Optional, Callable
from urllib.parse import urlparse

from src.config import Config
from src.utils.logger import setup_logger
from src.downloaders.youtube import download_youtube_audio, is_youtube_url
from src.downloaders.twitter import download_twitter_broadcast_audio, is_twitter_broadcast_url

logger = setup_logger(__name__)

# Type hint for downloader functions
DownloaderFunc = Callable[[str], Tuple[Optional[str], Optional[str]]]

# Map source types to their respective download functions and URL checkers
SOURCE_HANDLERS = {
    "youtube": {"checker": is_youtube_url, "downloader": download_youtube_audio},
    "twitter_broadcast": {"checker": is_twitter_broadcast_url, "downloader": download_twitter_broadcast_audio},
    # Add more sources here (e.g., direct m3u8, vimeo, etc.)
    # "m3u8": {"checker": is_m3u8_url, "downloader": download_generic_audio},
}

def identify_source(url: str) -> Optional[str]:
    """
    Identifies the source type of the video URL.

    Args:
        url (str): The URL to identify.

    Returns:
        Optional[str]: The identified source type (e.g., 'youtube', 'twitter_broadcast')
                       or None if unrecognized.
    """
    for source_type, handler in SOURCE_HANDLERS.items():
        if handler["checker"](url):
            logger.info(f"Identified URL source as: {source_type}")
            return source_type

    # Fallback check for direct m3u8 URLs (simple check)
    if url.lower().endswith(".m3u8"):
         logger.info("Identified URL source as: m3u8 (direct)")
         return "m3u8" # Requires a generic downloader

    logger.warning(f"Could not identify source for URL: {url}")
    return None

def download_generic_audio(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Downloads audio from a generic URL (like a direct m3u8) using yt-dlp.
    This is a fallback if no specific handler matched but yt-dlp might support it.

    Args:
        url (str): The URL to download from.

    Returns:
        Tuple[Optional[str], Optional[str]]: Path to the downloaded audio file and title, or (None, None).
    """
    logger.info(f"Attempting generic download using yt-dlp for: {url}")

    # Similar logic to twitter downloader, but simpler as no specific site interaction needed
    output_template = str(Config.OUTPUT_DIR / "%(title)s_generic_%(id)s.%(ext)s")
    final_audio_path = None
    video_title = None

    try:
        # Get title
        info_command = ["yt-dlp", "--get-title", "--no-warnings", url]
        title_process = subprocess.run(info_command, capture_output=True, text=True, check=False, encoding='utf-8') # check=False initially
        if title_process.returncode == 0:
            video_title = title_process.stdout.strip()
            logger.info(f"Extracted video title: {video_title}")
        else:
            logger.warning(f"Could not get title via yt-dlp for {url}. Using generic title.")
            video_title = "generic_audio" # Fallback title

        # Sanitize title
        sanitized_title = re.sub(r'[\\/*?:"<>|]', "_", video_title)
        expected_output_base = str(Config.OUTPUT_DIR / f"{sanitized_title}_generic_")

        # Download audio
        download_command = [
            "yt-dlp",
            "-f", Config.YT_DLP_FORMAT,
            "--no-warnings",
            "--output", output_template,
            url
        ]
        download_process = subprocess.run(download_command, capture_output=True, text=True, check=True, encoding='utf-8')
        logger.info("yt-dlp generic download process completed.")

        # Find downloaded file (same logic as twitter downloader)
        output_lines = download_process.stdout.splitlines() + download_process.stderr.splitlines()
        destination_pattern = re.compile(r"\[(?:download|ExtractAudio)\].*Destination: (.*)")
        actual_path_found = None
        for line in output_lines:
            match = destination_pattern.search(line)
            if match:
                actual_path_found = match.group(1).strip()
                if actual_path_found.lower().endswith(('.m4a', '.mp3', '.wav', '.ogg', '.aac', '.opus', '.webm')):
                    final_audio_path = actual_path_found
                    logger.info(f"Successfully downloaded generic audio file: {final_audio_path}")
                    break

        if not final_audio_path:
            logger.warning("Could not reliably determine the downloaded generic audio file path. Guessing...")
            import glob
            potential_files = glob.glob(expected_output_base + "*")
            audio_extensions = ('.m4a', '.mp3', '.wav', '.ogg', '.aac', '.opus', '.webm')
            audio_files = [f for f in potential_files if f.lower().endswith(audio_extensions)]
            if audio_files:
                 audio_files.sort(key=os.path.getmtime, reverse=True)
                 final_audio_path = audio_files[0]
                 logger.warning(f"Guessed generic audio file path: {final_audio_path}")
            else:
                 logger.error("Failed to find downloaded generic audio file.")
                 return None, video_title

        return final_audio_path, video_title

    except subprocess.CalledProcessError as e:
        logger.error(f"yt-dlp failed for generic URL {url}. Return code: {e.returncode}")
        logger.error(f"yt-dlp stdout: {e.stdout}")
        logger.error(f"yt-dlp stderr: {e.stderr}")
        return None, video_title # Return title if we got it, else None
    except FileNotFoundError:
        logger.error("yt-dlp command not found. Make sure yt-dlp is installed and in your system's PATH.")
        return None, None
    except Exception as e:
        logger.error(f"An unexpected error occurred during generic download for {url}: {e}", exc_info=True)
        return None, None


def download_audio(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Downloads audio from the given URL by identifying the source and calling the appropriate downloader.

    Args:
        url (str): The URL of the video/audio source.

    Returns:
        Tuple[Optional[str], Optional[str]]: Path to the downloaded audio file and the video title,
                                             or (None, None) on failure.
    """
    source_type = identify_source(url)

    if source_type and source_type in SOURCE_HANDLERS:
        downloader = SOURCE_HANDLERS[source_type]["downloader"]
        logger.info(f"Using '{source_type}' downloader for URL: {url}")
        return downloader(url)
    elif source_type == "m3u8":
         # Use the generic downloader for direct m3u8 links
         logger.info(f"Using generic downloader for direct m3u8 URL: {url}")
         return download_generic_audio(url)
    else:
        # Attempt generic download as a last resort
        logger.warning(f"Source for {url} unrecognized or no specific handler. Attempting generic download with yt-dlp.")
        return download_generic_audio(url)

