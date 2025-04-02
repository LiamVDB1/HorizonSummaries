"""
Functions for downloading videos from Twitter/Periscope.
"""

import os
import re
import tempfile
import logging
import requests
from typing import Tuple, Optional

import yt_dlp
from src.config import Config
from src.downloaders.common import extract_m3u8_url

logger = logging.getLogger("horizon_summaries")


def extract_m3u8_from_twitter_page(url: str) -> Optional[str]:
    """
    Extract m3u8 playlist URL from a Twitter page.

    Args:
        url (str): The Twitter URL

    Returns:
        Optional[str]: The m3u8 URL if found, None otherwise
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        # Try to extract the m3u8 URL from the page content
        m3u8_url = extract_m3u8_url(response.text)

        if m3u8_url:
            logger.info(f"Found m3u8 playlist in Twitter page: {m3u8_url}")
            return m3u8_url

        logger.warning("No m3u8 playlist found in Twitter page")
        return None

    except Exception as e:
        logger.error(f"Failed to extract m3u8 from Twitter page: {str(e)}")
        return None


def download_twitter_video(url: str) -> Tuple[str, str]:
    """
    Download a Twitter/Periscope video.

    Args:
        url (str): The Twitter/Periscope URL or direct m3u8 URL

    Returns:
        Tuple[str, str]: Path to the audio file and the video title
    """
    logger.info(f"Downloading Twitter/Periscope video: {url}")

    # Check if the URL is already an m3u8 playlist
    if '.m3u8' not in url:
        # Try to extract the m3u8 URL from the page
        m3u8_url = extract_m3u8_from_twitter_page(url)

        # If extraction failed, try using yt-dlp directly
        if not m3u8_url:
            logger.info("Falling back to direct yt-dlp download")
            return download_with_ytdlp(url)

        url = m3u8_url

    # Create a temp file path for the audio
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3", dir=Config.TEMP_DIR)
    temp_path = temp_file.name
    temp_file.close()

    # Configure yt-dlp options
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': temp_path,
        'retries': 10,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
    }

    try:
        # Generate a title based on the URL if it's a direct m3u8 URL
        video_title = generate_title_from_url(url)

        # Download and convert the video to mp3
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        logger.info(f"Twitter/Periscope video downloaded successfully: {video_title}")

        # Return the path to the audio file
        return temp_path, video_title

    except Exception as e:
        # Clean up the temp file if download failed
        if os.path.exists(temp_path):
            os.remove(temp_path)

        logger.error(f"Failed to download Twitter/Periscope video: {str(e)}")

        # Try fallback method
        logger.info("Trying fallback method with yt-dlp")
        return download_with_ytdlp(url)


def download_with_ytdlp(url: str) -> Tuple[str, str]:
    """
    Download video using yt-dlp's built-in extractors.

    Args:
        url (str): The video URL

    Returns:
        Tuple[str, str]: Path to the audio file and the video title
    """
    logger.info(f"Downloading with yt-dlp: {url}")

    # Create a temp file path for the audio
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3", dir=Config.TEMP_DIR)
    temp_path = temp_file.name
    temp_file.close()

    # Configure yt-dlp options
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': temp_path,
        'retries': 10,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    try:
        # Download and convert the video to mp3
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            video_title = info_dict.get('title', 'Unknown Title')
            if not video_title or video_title == 'Unknown Title':
                video_title = generate_title_from_url(url)

        logger.info(f"Video downloaded successfully with yt-dlp: {video_title}")

        # Return the path to the audio file
        return temp_path, video_title.replace('/', '_').replace('\\', '_')

    except Exception as e:
        # Clean up the temp file if download failed
        if os.path.exists(temp_path):
            os.remove(temp_path)

        logger.error(f"Failed to download with yt-dlp: {str(e)}")
        raise


def generate_title_from_url(url: str) -> str:
    """
    Generate a title from a URL.

    Args:
        url (str): The URL

    Returns:
        str: A generated title
    """
    # Extract from playlist URL if possible
    playlist_match = re.search(r'playlist_(\d+)\.m3u8', url)
    if playlist_match:
        return f"Twitter_Broadcast_{playlist_match.group(1)}"

    # For Periscope URLs, extract the broadcast ID
    periscope_match = re.search(r'([a-zA-Z0-9_-]{10,})(?:/|$)', url)
    if periscope_match:
        return f"Periscope_Broadcast_{periscope_match.group(1)}"

    # If no matches, use a generic title with timestamp
    import time
    timestamp = int(time.time())
    return f"Twitter_Video_{timestamp}"