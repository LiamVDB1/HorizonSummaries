"""
Handles interactions with Google Cloud Vertex AI models for various LLM tasks.
"""
import os
import asyncio
import random
from typing import Optional, Dict, Any

try:
    import vertexai
    from vertexai.generative_models import GenerativeModel
    from google.cloud import aiplatform
    from google import genai
    from google.genai.types import GenerateContentConfig
except ImportError:
    raise ImportError("Vertex AI libraries not found. Please install google-cloud-aiplatform and google-genai")

from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class QuotaExceededException(Exception):
    """Exception raised when API quota is exceeded."""
    pass

class VertexAIGenerator:
    """Class for generating content using Google's VertexAI."""

    def __init__(self):
        """Initialize VertexAI with project settings and credentials."""
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = Config.GOOGLE_APPLICATION_CREDENTIALS
        self.client = genai.Client(vertexai=True, project=Config.GOOGLE_PROJECT_ID, location=Config.GOOGLE_REGION)

        self.client = genai.Client(
            vertexai=True,
            project=Config.GOOGLE_PROJECT_ID,
            location=Config.GOOGLE_REGION,
        )

        # Rate limiting parameters
        self.max_retries = 3
        self.initial_retry_delay = 1  # Initial delay in seconds
        self.max_retry_delay = 32.0  # Maximum delay in seconds
        self.jitter_factor = 0.1  # Add randomness to retry delays

        logger.info(f"Initialized VertexAIGenerator")

    def _calculate_retry_delay(self, retry_count: int) -> float:
        """Calculate retry delay with exponential backoff and jitter."""
        delay = min(self.max_retry_delay,
                   self.initial_retry_delay * (2 ** retry_count))
        jitter = delay * self.jitter_factor * random.uniform(-1, 1)
        return delay + jitter

    def _handle_quota_error(self, error_message: str) -> bool:
        """Check if the error is related to quota exceeded."""
        quota_indicators = [
            "429 Quota exceeded",
            "exceeds quota",
            "429 RESOURCE_EXHAUSTED",
            "prediction request quota exceeded",
            "Please try again later with backoff"
        ]
        return any(indicator in error_message for indicator in quota_indicators)

    async def generate_response_with_retry(
            self,
            prompt: str,
            model: str = Config.DEFAULT_MODEL,
            temperature: Optional[float] = None,
            top_p: Optional[float] = None,
            top_k: Optional[float] = None,
            max_output_tokens: Optional[int] = None,
            presence_penalty: Optional[float] = None,
            frequency_penalty: Optional[float] = None,
            response_mime: Optional[str] = None,
            response_schema: Optional[Dict[str, Any]] = None,
            system_instruction: Optional[str] = None,
    ) -> Dict:
        """
        Generate a response using VertexAI with retry logic for quota errors.
        """
        retry_count = 0
        last_error = None
        logger.info(f"Generating response with retry logic")
        logger.debug(f"Prompt: {prompt}")

        while retry_count <= self.max_retries:
            try:
                return await self.generate_response(
                    prompt=prompt,
                    model=model,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                    max_output_tokens=max_output_tokens,
                    presence_penalty=presence_penalty,
                    frequency_penalty=frequency_penalty,
                    response_mime=response_mime,
                    response_schema=response_schema,
                    system_instruction=system_instruction
                )

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Error in generate_response: {last_error}")

                if retry_count >= self.max_retries:
                    logger.error(f"Max retries ({self.max_retries}) reached")
                    raise e

                delay = self._calculate_retry_delay(retry_count)
                logger.info(
                    f"Retrying in {delay:.2f} seconds (attempt {retry_count + 1}/{self.max_retries})")
                await asyncio.sleep(delay)
                retry_count += 1

                # Try lesser model on alternate retries if not already using it
                if not model == Config.LESSER_MODEL and retry_count > 2 and retry_count % 2 == 1:
                    logger.info("Attempting with lesser model...")
                    model = Config.LESSER_MODEL

    async def generate_response(
            self,
            prompt: str,
            model: str = Config.DEFAULT_MODEL,
            temperature: Optional[float] = None,
            top_p: Optional[float] = None,
            top_k: Optional[float] = None,
            max_output_tokens: Optional[int] = None,
            presence_penalty: Optional[float] = None,
            frequency_penalty: Optional[float] = None,
            response_mime: Optional[str] = None,
            response_schema: Optional[Dict[str, Any]] = None,
            system_instruction: Optional[str] = None,
    ) -> Dict:
        """
        Generate a response using VertexAI asynchronously.
        """
        generation_config = GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            candidate_count=None,
            max_output_tokens=max_output_tokens,
            stop_sequences=None,
            presence_penalty=presence_penalty,
            frequency_penalty=frequency_penalty,
            response_mime_type=response_mime,
            response_schema=response_schema,
            response_modalities=None
        )

        # Run the potentially blocking generate_content in an executor
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.models.generate_content(
                model=model,
                contents=prompt,
                config=generation_config
            )
        )

        metadata = {
            "prompt_token_count": response.usage_metadata.prompt_token_count,
            "candidates_token_count": response.usage_metadata.candidates_token_count,
            "total_token_count": response.usage_metadata.total_token_count,
            "model_used": model
        }

        return {"content": response.text, "metadata": metadata}


async def main():
    num_expansions = 3

    json_schema = {
        "type": "array",
        "items": {
            "type": "string"
        },
        "minItems": num_expansions,
        "maxItems": num_expansions,
        "description": "Array of query variations including the original query"
    }

    generator = VertexAIGenerator()
    result = await generator.generate_response_with_retry(
        "What is the meaning of life?"
    )
    print(result)

if __name__ == "__main__":
    asyncio.run(main())