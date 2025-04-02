"""
Functions for downloading videos from YouTube.
"""

import os
import tempfile
import logging
import requests
from typing import Tuple
import yt_dlp

from src.config import Config

logger = logging.getLogger("horizon_summaries")


def download_youtube_video(url: str) -> Tuple[str, str]:
    """
    Download a YouTube video and extract its audio.

    Args:
        url (str): The YouTube URL

    Returns:
        Tuple[str, str]: Path to the audio file and the video title
    """
    logger.info(f"Downloading YouTube video: {url}")

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
        # Download and convert the video to mp3
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract video info to get the title
            info_dict = ydl.extract_info(url, download=True)
            video_title = info_dict.get('title', 'Unknown Title')
            thumbnail_url = info_dict.get('thumbnail', None)

            # Download the thumbnail if the URL is available
            if thumbnail_url:
                try:
                    thumbnail_response = requests.get(thumbnail_url)
                    if thumbnail_response.status_code == 200:
                        thumbnail_path = os.path.join(Config.OUTPUT_DIR, f"{video_title}_thumbnail.jpg")
                        with open(thumbnail_path, 'wb') as f:
                            f.write(thumbnail_response.content)
                        logger.info(f"Thumbnail downloaded to {thumbnail_path}")
                except Exception as e:
                    logger.warning(f"Failed to download thumbnail: {str(e)}")

        logger.info(f"YouTube video downloaded successfully: {video_title}")

        # Return the path to the audio file
        return temp_path, video_title.replace('/', '_').replace('\\', '_')

    except Exception as e:
        # Clean up the temp file if download failed
        if os.path.exists(temp_path):
            os.remove(temp_path)

        logger.error(f"Failed to download YouTube video: {str(e)}")
        raise