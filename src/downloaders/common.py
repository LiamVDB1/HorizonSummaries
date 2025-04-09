"""
Common utilities for identifying video sources and orchestrating downloads.
"""

import re
from typing import Optional
from urllib.parse import urlparse

from src.config import Config
from src.utils.logger import setup_logger
from src.downloaders.yt_dlp_audio_downloader import download_audio as yt_dlp_download

logger = setup_logger(__name__)

def is_youtube_url(url: str) -> bool:
    """Checks if the URL is a valid YouTube URL."""
    parsed_url = urlparse(url)
    return (parsed_url.netloc.endswith("youtube.com") or
            parsed_url.netloc == "youtu.be")

def is_twitter_broadcast_url(url: str) -> bool:
    """Checks if the URL is a Twitter (X) broadcast URL."""
    parsed_url = urlparse(url)
    return (parsed_url.netloc in ["twitter.com", "x.com"] and
            parsed_url.path.startswith("/i/broadcasts/"))

def is_m3u8_url(url: str) -> bool:
    """Checks if the URL is a direct M3U8 playlist URL."""
    return url.lower().endswith('.m3u8') or '.m3u8?' in url.lower()

# Map source types to their respective URL checkers
SOURCE_TYPES = {
    "youtube": is_youtube_url,
    "twitter_broadcast": is_twitter_broadcast_url,
    "m3u8": is_m3u8_url,
    # Add more source types and checkers as needed
}

def identify_source(url: str) -> str:
    """
    Identifies the source type of the video URL.

    Args:
        url (str): The URL to identify.

    Returns:
        str: The identified source type or "generic" if unrecognized.
    """
    for source_type, checker in SOURCE_TYPES.items():
        if checker(url):
            logger.info(f"Identified URL source as: {source_type}")
            return source_type

    logger.info(f"Could not identify specific source for URL: {url}, treating as generic")
    return "generic"

def download_audio(url: str):
    """
    Downloads audio from the given URL by identifying the source type and using yt-dlp.

    Args:
        url (str): The URL of the video/audio source.

    Returns:
        Tuple[Optional[str], Optional[str]]: Path to the downloaded audio file and the title,
                                            or (None, None) on failure.
    """
    source_type = identify_source(url)
    logger.info(f"Using yt-dlp to download from {source_type} URL: {url}")
    return yt_dlp_download(url, source_type)