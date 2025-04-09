"""
Video downloading utilities for various platforms.
"""

from src.downloaders.common import (
    download_audio,
    identify_source,
    download_generic_audio
)

from src.downloaders.youtube import (
    download_youtube_audio,
    is_youtube_url
)
from src.downloaders.twitter import (
    download_twitter_broadcast_audio,
    is_twitter_broadcast_url
)

__all__ = [
    # Main API function
    "download_audio",

    # Source identification
    "identify_source",

    # Platform-specific downloads (for direct use if needed)
    "download_youtube_audio",
    "download_twitter_broadcast_audio",
    "download_generic_audio",

    # URL validators
    "is_youtube_url",
    "is_twitter_broadcast_url"
]