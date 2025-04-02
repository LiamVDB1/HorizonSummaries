"""
Common utilities for downloading videos from various sources.
"""

import os
import re
import tempfile
import logging
from typing import Tuple, Optional
from urllib.parse import urlparse

from src.config import Config
from src.downloaders.youtube import download_youtube_video
from src.downloaders.twitter import download_twitter_video

logger = logging.getLogger("horizon_summaries")


def identify_source(url: str) -> str:
    """
    Identify the source type of a video URL.

    Args:
        url (str): The URL to identify

    Returns:
        str: The source type ('youtube', 'twitter', 'periscope', 'unknown')
    """
    parsed_url = urlparse(url)

    # Check for YouTube
    if 'youtube.com' in parsed_url.netloc or 'youtu.be' in parsed_url.netloc:
        return 'youtube'

    # Check for Twitter
    if 'twitter.com' in parsed_url.netloc or 'x.com' in parsed_url.netloc:
        return 'twitter'

    # Check for Periscope (Twitter broadcast)
    if 'pscp.tv' in parsed_url.netloc or '.video.pscp.tv' in parsed_url.netloc:
        return 'periscope'

    # Check for m3u8 playlist in URL
    if '.m3u8' in url:
        return 'm3u8'

    return 'unknown'


def download_audio(url: str) -> Tuple[str, str]:
    """
    Download audio from a video URL.

    Args:
        url (str): The URL to download from

    Returns:
        Tuple[str, str]: Path to the downloaded audio file and the video title
    """
    # Identify the source
    source_type = identify_source(url)

    # Create temp directory if it doesn't exist
    os.makedirs(Config.TEMP_DIR, exist_ok=True)

    # Download based on source type
    if source_type == 'youtube':
        return download_youtube_video(url)
    elif source_type in ['twitter', 'periscope', 'm3u8']:
        return download_twitter_video(url)
    else:
        raise ValueError(f"Unsupported source type: {source_type}")


def extract_m3u8_url(content: str) -> Optional[str]:
    """
    Extract m3u8 playlist URL from content.

    Args:
        content (str): The content to search for m3u8 URLs

    Returns:
        Optional[str]: The m3u8 URL if found, None otherwise
    """
    # Look for m3u8 playlist URL patterns
    pattern = r'(https?://[^\s\'\"]+\.m3u8[^\s\'\"]*)'
    matches = re.findall(pattern, content)

    if matches:
        return matches[0]

    return None