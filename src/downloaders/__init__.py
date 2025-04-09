"""
Video downloading utilities for various platforms.
"""

from src.downloaders.common import (
    download_audio,
    identify_source,
    is_youtube_url,
    is_twitter_broadcast_url,
    is_m3u8_url
)

__all__ = [
    # Main API function
    "download_audio",

    # Source identification
    "identify_source",
    "is_youtube_url",
    "is_twitter_broadcast_url",
    "is_m3u8_url"
]