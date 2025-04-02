"""
VertexAI client for interacting with Google's AI models.
"""

import os
import random
import asyncio
import logging
import json
from typing import Dict, List, Optional, Any, Union

from google.genai.types import GenerateContentConfig
from google import genai

from src.config import Config

logger = logging.getLogger("horizon_summaries")


class QuotaExceededException(Exception):
    """Exception raised when API quota is exceeded."""
    pass


class VertexAIClient:
    """Client for interacting with Google's VertexAI."""

    _instance = None

    def __new__(cls):
        """Singleton pattern to ensure only one client instance exists."""
        if cls._instance is None:
            cls._instance = super(VertexAIClient, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize the VertexAI client with credentials."""
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        self.client = genai.Client(
            vertexai=True,
            project=os.getenv("GOOGLE_PROJECT_ID"),
            location=os.getenv("GOOGLE_REGION")
        )

        self.model_id = None
        self.set_model_id()

        # Rate limiting parameters
        self.max_retries = 3
        self.initial_retry_delay = 1  # Initial delay in seconds
        self.max_retry_delay = 32.0  # Maximum delay in seconds
        self.jitter_factor = 0.1  # Add randomness to retry delays

        logger.info(f"Initialized VertexAIClient with model {self.model_id}")

    def set_model_id(self, lesser_model: bool = False):
        """Set the model based on whether to use the lesser model or not."""
        self.model_id = Config.LESSER_MODEL if lesser_model else Config.DEFAULT_MODEL
        logger.info(f"Using model: {self.model_id}")

    def _calculate_retry_delay(self, retry_count: int) -> float:
        """Calculate retry delay with exponential backoff and jitter."""
        delay = min(self.max_retry_delay, self.initial_retry_delay * (2 ** retry_count))
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

    async def generate_response(
            self,
            prompt: str,
            temperature: Optional[float] = None,
            top_p: Optional[float] = None,
            top_k: Optional[float] = None,
            max_output_tokens: Optional[int] = None,
            presence_penalty: Optional[float] = None,
            frequency_penalty: Optional[float] = None,
            response_mime: Optional[str] = None,
            response_schema: Optional[Dict[str, Any]] = None,
            lesser_model: bool = False,
    ) -> Dict:
        """
        Generate a response using VertexAI asynchronously.

        Args:
            prompt (str): The prompt to generate from
            temperature (Optional[float], optional): Temperature parameter. Defaults to None.
            top_p (Optional[float], optional): Top-p parameter. Defaults to None.
            top_k (Optional[float], optional): Top-k parameter. Defaults to None.
            max_output_tokens (Optional[int], optional): Maximum output tokens. Defaults to None.
            presence_penalty (Optional[float], optional): Presence penalty. Defaults to None.
            frequency_penalty (Optional[float], optional): Frequency penalty. Defaults to None.
            response_mime (Optional[str], optional): Response MIME type. Defaults to None.
            response_schema (Optional[Dict[str, Any]], optional): Response schema. Defaults to None.
            lesser_model (bool, optional): Whether to use the lesser model. Defaults to False.

        Returns:
            Dict: Response dictionary with content and metadata
        """
        if lesser_model or self.model_id is None:
            self.set_model_id(lesser_model)

        generation_config = GenerateContentConfig(
            system_instruction=None,
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
                model=self.model_id,
                contents=prompt,
                config=generation_config
            )
        )

        metadata = {
            "prompt_token_count": response.usage_metadata.prompt_token_count,
            "candidates_token_count": response.usage_metadata.candidates_token_count,
            "total_token_count": response.usage_metadata.total_token_count,
            "model_used": "lesser" if lesser_model else "standard"
        }

        return {"content": response.text, "metadata": metadata}

    async def generate_response_with_retry(
            self,
            prompt: str,
            temperature: Optional[float] = None,
            top_p: Optional[float] = None,
            top_k: Optional[float] = None,
            max_output_tokens: Optional[int] = None,
            presence_penalty: Optional[float] = None,
            frequency_penalty: Optional[float] = None,
            response_mime: Optional[str] = None,
            response_schema: Optional[Dict[str, Any]] = None,
            lesser_model: bool = False,
    ) -> Dict:
        """
        Generate a response using VertexAI with retry logic for quota errors.

        Args:
            prompt (str): The prompt to generate from
            temperature (Optional[float], optional): Temperature parameter. Defaults to None.
            top_p (Optional[float], optional): Top-p parameter. Defaults to None.
            top_k (Optional[float], optional): Top-k parameter. Defaults to None.
            max_output_tokens (Optional[int], optional): Maximum output tokens. Defaults to None.
            presence_penalty (Optional[float], optional): Presence penalty. Defaults to None.
            frequency_penalty (Optional[float], optional): Frequency penalty. Defaults to None.
            response_mime (Optional[str], optional): Response MIME type. Defaults to None.
            response_schema (Optional[Dict[str, Any]], optional): Response schema. Defaults to None.
            lesser_model (bool, optional): Whether to use the lesser model. Defaults to False.

        Returns:
            Dict: Response dictionary with content and metadata

        Raises:
            QuotaExceededException: If max retries exceeded due to quota limits
        """
        retry_count = 0
        last_error = None

        while retry_count <= self.max_retries:
            try:
                return await self.generate_response(
                    prompt=prompt,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                    max_output_tokens=max_output_tokens,
                    presence_penalty=presence_penalty,
                    frequency_penalty=frequency_penalty,
                    response_mime=response_mime,
                    response_schema=response_schema,
                    lesser_model=lesser_model
                )

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Error in generate_response: {last_error}")

                # Check if it's a quota error
                if self._handle_quota_error(last_error):
                    if retry_count >= self.max_retries:
                        logger.error(f"Max retries ({self.max_retries}) exceeded due to quota limits.")
                        raise QuotaExceededException(
                            f"Max retries ({self.max_retries}) exceeded due to quota limits. "
                            "Consider implementing request queuing or increasing quotas."
                        )

                    delay = self._calculate_retry_delay(retry_count)
                    logger.info(
                        f"Quota exceeded, retrying in {delay:.2f} seconds (attempt {retry_count + 1}/{self.max_retries})")
                    await asyncio.sleep(delay)
                    retry_count += 1

                    # Try lesser model on alternate retries if not already using it
                    if not lesser_model and retry_count % 2 == 1:
                        logger.info("Attempting with lesser model...")
                        lesser_model = True
                        self.set_model_id(lesser_model=True)
                else:
                    # Not a quota error, raise immediately
                    logger.error(f"Error generating response: {last_error}")
                    raise

        # This should never be reached due to the raise in the loop
        raise QuotaExceededException("Unexpected state in retry loop")

    async def get_json_response(
            self,
            prompt: str,
            json_schema: Dict,
            temperature: float = 0.2,
            max_output_tokens: int = 2048,
            lesser_model: bool = False
    ) -> Any:
        """
        Get a structured JSON response from the model.

        Args:
            prompt (str): The prompt to generate from
            json_schema (Dict): JSON schema for response validation
            temperature (float, optional): Temperature parameter. Defaults to 0.2.
            max_output_tokens (int, optional): Maximum output tokens. Defaults to 2048.
            lesser_model (bool, optional): Whether to use the lesser model. Defaults to False.

        Returns:
            Any: Parsed JSON response
        """
        try:
            response = await self.generate_response_with_retry(
                prompt=prompt,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                response_mime="application/json",
                response_schema=json_schema,
                lesser_model=lesser_model
            )

            # Parse the JSON response
            return json.loads(response["content"])

        except Exception as e:
            logger.error(f"Error getting JSON response: {str(e)}")
            # Return empty result in case of error
            if isinstance(json_schema.get("type"), str) and json_schema["type"] == "object":
                return {}
            elif isinstance(json_schema.get("type"), str) and json_schema["type"] == "array":
                return []
            else:
                return None