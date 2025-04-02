"""
Transcription functionalities using FalAI Whisper.
"""

import os
import asyncio
import tempfile
import logging
from typing import List, Optional

import fal_client
from fal_client import InProgress, Queued, Completed
from pydub import AudioSegment

from src.config import Config

logger = logging.getLogger("horizon_summaries")


def split_audio(file_path: str, max_size_mb: int = None) -> List[str]:
    """
    Split audio file into smaller chunks if it exceeds the maximum size.

    Args:
        file_path (str): Path to the audio file
        max_size_mb (int, optional): Maximum size in MB. Defaults to Config.MAX_AUDIO_SIZE_MB.

    Returns:
        List[str]: List of paths to the audio chunks
    """
    max_size_mb = max_size_mb or Config.MAX_AUDIO_SIZE_MB
    logger.info(f"Checking if audio needs to be split (max size: {max_size_mb}MB)")

    # Load the audio file using pydub
    audio = AudioSegment.from_file(file_path)

    # Determine the chunk size based on the maximum file size allowed
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb <= max_size_mb:
        # If the file size is within the limit, create a temporary copy
        logger.info(f"Audio size ({file_size_mb:.2f}MB) is within limit, no splitting needed")
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3", dir=Config.TEMP_DIR)
        audio.export(temp_file.name, format="mp3")
        return [temp_file.name]

    # Split the audio into smaller chunks if it exceeds the maximum file size
    logger.info(f"Audio size ({file_size_mb:.2f}MB) exceeds limit, splitting into {max_size_mb}MB chunks")
    chunk_length_ms = len(audio) * (max_size_mb / file_size_mb)
    overlap_ms = 200  # 0.2-second overlap
    chunks = [audio[i:i + int(chunk_length_ms) + overlap_ms] for i in range(0, len(audio), int(chunk_length_ms))]

    # Export each chunk to a temporary file
    chunk_files = []
    for i, chunk in enumerate(chunks):
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f"_chunk{i}.mp3", dir=Config.TEMP_DIR)
        chunk.export(temp_file.name, format="mp3")
        chunk_files.append(temp_file.name)

    logger.info(f"Split audio into {len(chunk_files)} chunks")
    return chunk_files


async def submit_transcription_job(audio_url: str) -> str:
    """
    Submit a transcription job to FalAI.

    Args:
        audio_url (str): URL to the audio file

    Returns:
        str: Request ID
    """
    handler = await fal_client.submit_async(
        "fal-ai/wizper",
        arguments={
            "audio_url": audio_url
        },
    )
    return handler.request_id


async def transcribe_chunk(temp_file_path: str, max_tries: int = 5, current_retry: int = 0) -> Optional[str]:
    """
    Transcribe an audio chunk using FalAI Whisper.

    Args:
        temp_file_path (str): Path to the audio chunk
        max_tries (int, optional): Maximum number of retry attempts. Defaults to 5.
        current_retry (int, optional): Current retry attempt. Defaults to 0.

    Returns:
        Optional[str]: Transcription text if successful, None otherwise
    """
    try:
        logger.info(f"Uploading audio chunk: {os.path.basename(temp_file_path)}")
        data_url = await fal_client.upload_file_async(temp_file_path)

        logger.info(f"Submitting transcription job for chunk: {os.path.basename(temp_file_path)}")
        request_id = await submit_transcription_job(data_url)
        logger.info(f"Submitted transcription job with ID: {request_id}")

        # Check job status
        status = await fal_client.status_async("fal-ai/wizper", request_id, with_logs=True)

        # Wait for job to complete
        while isinstance(status, InProgress) or isinstance(status, Queued):
            logger.info(f"Job status: {type(status).__name__}, waiting...")
            await asyncio.sleep(5)
            status = await fal_client.status_async("fal-ai/wizper", request_id, with_logs=True)

        # Check if job completed successfully
        if isinstance(status, Completed):
            logger.info(f"Transcription complete for chunk: {os.path.basename(temp_file_path)}")
            result = await fal_client.result_async("fal-ai/wizper", request_id)
            return result["text"]
        else:
            logger.warning(f"Job failed with status: {type(status).__name__}")
            if current_retry < max_tries:
                logger.info(f"Retrying transcription (attempt {current_retry + 1}/{max_tries})")
                return await transcribe_chunk(temp_file_path, max_tries, current_retry + 1)
            else:
                logger.error(f"Max retries reached. Failed to transcribe {os.path.basename(temp_file_path)}")
                return None

    except Exception as e:
        logger.error(f"Error during transcription: {str(e)}")
        if current_retry < max_tries:
            logger.info(f"Retrying transcription after error (attempt {current_retry + 1}/{max_tries})")
            await asyncio.sleep(2 ** current_retry)  # Exponential backoff
            return await transcribe_chunk(temp_file_path, max_tries, current_retry + 1)
        else:
            logger.error(f"Max retries reached. Failed to transcribe {os.path.basename(temp_file_path)}")
            return None


async def transcribe_audio_async(file_path: str) -> Optional[str]:
    """
    Transcribe an audio file using FalAI Whisper.

    Args:
        file_path (str): Path to the audio file

    Returns:
        Optional[str]: Transcription text if successful, None otherwise
    """
    # Set FalAI API token
    token = os.environ.get("FALAI_TOKEN")
    if not token:
        logger.error("FALAI_TOKEN environment variable is not set")
        raise ValueError("FALAI_TOKEN environment variable is not set")

    os.environ["FAL_KEY"] = token

    # Make sure the file exists
    if not os.path.exists(file_path):
        logger.error(f"Audio file not found: {file_path}")
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    # Split the audio file if it exceeds the maximum allowed size
    audio_files = split_audio(file_path)

    try:
        # Transcribe each chunk asynchronously
        logger.info(f"Transcribing {len(audio_files)} audio chunks")
        tasks = [transcribe_chunk(chunk_path) for chunk_path in audio_files]
        transcriptions = await asyncio.gather(*tasks)

        # Filter out None values (failed transcriptions)
        transcriptions = [t for t in transcriptions if t]

        if not transcriptions:
            logger.error("All transcription attempts failed")
            return None

        # Combine all transcriptions
        complete_transcription = " ".join(transcriptions)
        logger.info(f"Transcription complete: {len(complete_transcription)} characters")

        return complete_transcription

    finally:
        # Clean up temporary audio files
        for audio_file in audio_files:
            if os.path.exists(audio_file):
                os.remove(audio_file)
                logger.info(f"Removed temporary file: {audio_file}")


def transcribe_audio(file_path: str) -> str:
    """
    Synchronous wrapper for transcribe_audio_async.

    Args:
        file_path (str): Path to the audio file

    Returns:
        str: Transcription text
    """
    result = asyncio.run(transcribe_audio_async(file_path))
    if result is None:
        raise RuntimeError("Transcription failed")
    return result