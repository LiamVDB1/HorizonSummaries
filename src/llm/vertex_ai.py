"""
Handles interactions with Google Cloud Vertex AI models for various LLM tasks.
"""
import os
import logging
import json
from typing import Optional, List, Dict, Any

# Import the Vertex AI SDK AFTER setting credentials (usually done via env var)
try:
    import vertexai
    from vertexai.generative_models import GenerativeModel, Part, HarmCategory, HarmBlockThreshold
    from google.cloud import aiplatform # To initialize
except ImportError:
    raise ImportError("Vertex AI libraries not found. Please install google-cloud-aiplatform")

from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# --- Initialization ---
_initialized = False

def initialize_vertex_ai():
    """Initializes the Vertex AI client."""
    global _initialized
    if _initialized:
        return

    try:
        logger.info(f"Initializing Vertex AI with Project ID: {Config.GOOGLE_PROJECT_ID}, Region: {Config.GOOGLE_REGION}")
        # Ensure credentials are set via GOOGLE_APPLICATION_CREDENTIALS env var
        aiplatform.init(
            project=Config.GOOGLE_PROJECT_ID,
            location=Config.GOOGLE_REGION,
            # credentials=credentials # Usually handled by env var
        )
        vertexai.init(project=Config.GOOGLE_PROJECT_ID, location=Config.GOOGLE_REGION)
        _initialized = True
        logger.info("Vertex AI initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Vertex AI: {e}", exc_info=True)
        raise

# --- Core Generation Function ---

async def generate_text(
    prompt: str,
    model_name: str = Config.DEFAULT_MODEL,
    temperature: float = 0.7,
    max_output_tokens: int = 8192, # Increased default for potentially long summaries/analyses
    top_p: float = 1.0,
    top_k: int = 40,
    system_instruction: Optional[str] = None,
    safety_settings: Optional[Dict[HarmCategory, HarmBlockThreshold]] = None,
) -> str:
    """
    Generates text using a specified Vertex AI model.

    Args:
        prompt (str): The main input prompt for the model.
        model_name (str): The name of the Vertex AI model to use.
        temperature (float): Controls randomness (0.0 = deterministic, 1.0 = max creativity).
        max_output_tokens (int): Maximum number of tokens in the response.
        top_p (float): Nucleus sampling parameter.
        top_k (int): Top-k sampling parameter.
        system_instruction (str, optional): System-level instructions for the model.
        safety_settings (dict, optional): Configuration for content safety filters.

    Returns:
        str: The generated text content.

    Raises:
        ValueError: If Vertex AI is not initialized.
        Exception: For errors during API call.
    """
    if not _initialized:
        initialize_vertex_ai() # Attempt initialization if not done

    if not _initialized: # Check again after attempt
        raise ValueError("Vertex AI is not initialized. Call initialize_vertex_ai() first or check credentials.")

    logger.debug(f"Generating text with model: {model_name}, Temp: {temperature}")
    logger.debug(f"Prompt (first 100 chars): {prompt[:100]}...")

    try:
        model = GenerativeModel(
            model_name,
            system_instruction=system_instruction if system_instruction else None
        )

        # Default safety settings (adjust as needed)
        if safety_settings is None:
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }

        generation_config = {
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "max_output_tokens": max_output_tokens,
        }

        # Use async generation if available and needed, otherwise sync
        # Note: As of early 2024, generate_content is sync, but SDK might evolve.
        # For truly async, consider libraries like `google-cloud-aiplatform[async]`
        # or running sync calls in an executor. Sticking to sync for now.
        response = model.generate_content(
            [prompt], # Content can be a list of strings or Parts
            generation_config=generation_config,
            safety_settings=safety_settings,
            stream=False, # Get the full response at once
        )

        # Handle potential blocked responses or empty results
        if not response.candidates:
             logger.warning("Vertex AI response has no candidates. Possible safety block or empty generation.")
             # Check finish_reason if available
             if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                 logger.error(f"Prompt blocked due to: {response.prompt_feedback.block_reason}")
                 raise ValueError(f"Vertex AI prompt blocked: {response.prompt_feedback.block_reason}")
             elif response.candidates and response.candidates[0].finish_reason.name != "STOP":
                 logger.error(f"Generation stopped unexpectedly: {response.candidates[0].finish_reason.name}")
                 raise ValueError(f"Vertex AI generation failed: {response.candidates[0].finish_reason.name}")
             else:
                 logger.warning("Received no candidates from Vertex AI, returning empty string.")
                 return "" # Or raise an error

        # Extract text from the first candidate
        # Assuming the response structure has candidates[0].content.parts[0].text
        if response.candidates[0].content and response.candidates[0].content.parts:
            generated_text = response.candidates[0].content.parts[0].text
            logger.debug(f"Generated text (first 100 chars): {generated_text[:100]}...")
            return generated_text
        else:
            logger.warning("Vertex AI response structure unexpected or content/parts missing.")
            return "" # Or raise an error

    except Exception as e:
        logger.error(f"Error during Vertex AI text generation: {e}", exc_info=True)
        # Consider adding retries here if appropriate
        raise # Re-raise the exception after logging

# --- Specific Task Functions ---

async def generate_summary(
        transcript: str,
        prompt_template: str,
        topics: List[Dict[str, Any]],
        model_name: str = Config.SUMMARIZATION_MODEL,
        **kwargs  # Allow passing other generate_text args like temperature
) -> str:
    """
    Generates a summary for a given transcript using a specific prompt template.

    Args:
        transcript (str): The text content to summarize.
        prompt_template (str): The template string for the summarization prompt.
                               Should contain placeholders like {transcript} and {topics}.
        topics (list): A list of key topics extracted from the transcript (either strings or
                      rich topic objects with metadata).
        model_name (str): The Vertex AI model to use for summarization.
        **kwargs: Additional arguments passed to generate_text.

    Returns:
        str: The generated summary.
    """
    logger.info(f"Generating summary using model: {model_name}")

    # Format topics based on their structure
    if topics and isinstance(topics[0], dict):
        # Rich topic format - create a detailed topics section
        topics_formatted = "\n\n**Key Topics:**\n"
        for topic in topics:
            relevance = topic.get('relevance', 'medium')
            confidence = topic.get('confidence', 0.7)
            # Only include high and medium relevance topics with decent confidence
            if relevance in ['high', 'medium'] and confidence >= 0.7:
                topics_formatted += f"\n### {topic['topic']}\n"

                # Add key points if available
                if 'key_points' in topic and topic['key_points']:
                    topics_formatted += "Key points:\n"
                    for point in topic['key_points']:
                        topics_formatted += f"- {point}\n"

                # Add category if available
                if 'category' in topic and topic['category']:
                    topics_formatted += f"Category: {topic['category']}\n"
    else:
        # Simple format - just comma-separated topics
        topics_formatted = ", ".join(topics) if topics else "No specific topics extracted"

    # Format the prompt
    prompt = prompt_template.format(
        transcript=transcript,
        topics=topics_formatted
    )

    # Define a system instruction specific to summarization
    system_instruction = """You are an expert summarizer specializing in blockchain and crypto project communications, particularly for the Jupiter ecosystem on Solana. Your goal is to create clear, concise, and engaging summaries from transcripts. Focus on key decisions, announcements, technical details, community sentiment, and action items. Use Markdown formatting for readability."""

    summary = await generate_text(
        prompt=prompt,
        model_name=model_name,
        system_instruction=system_instruction,
        **kwargs
    )
    return summary

# --- Helper to Parse JSON from LLM Output ---

def parse_json_from_llm(llm_output: str, description: str = "LLM response") -> Optional[Any]:
    """
    Attempts to parse a JSON object potentially embedded in LLM text output.
    Handles common issues like markdown code fences.

    Args:
        llm_output (str): The raw text output from the LLM.
        description (str): A description for logging purposes (e.g., "term analysis").

    Returns:
        Optional[Any]: The parsed JSON object (dict, list, etc.) or None if parsing fails.
    """
    logger.debug(f"Attempting to parse JSON from {description}: {llm_output[:200]}...") # Log start

    # Clean common markdown fences
    cleaned_output = llm_output.strip()
    if cleaned_output.startswith("```json"):
        cleaned_output = cleaned_output[7:]
    elif cleaned_output.startswith("```"):
         cleaned_output = cleaned_output[3:]

    if cleaned_output.endswith("```"):
        cleaned_output = cleaned_output[:-3]

    cleaned_output = cleaned_output.strip()

    try:
        # Attempt to parse directly
        parsed_json = json.loads(cleaned_output)
        logger.debug(f"Successfully parsed JSON for {description}.")
        return parsed_json
    except json.JSONDecodeError as e:
        logger.warning(f"Initial JSON parsing failed for {description}: {e}. Raw output: {llm_output}")
        # Optional: Add more sophisticated cleaning or regex extraction here if needed
        # For example, try finding the first '{' and last '}'
        try:
            start = cleaned_output.find('{')
            end = cleaned_output.rfind('}')
            if start != -1 and end != -1 and start < end:
                potential_json = cleaned_output[start:end+1]
                parsed_json = json.loads(potential_json)
                logger.warning(f"Successfully parsed JSON for {description} after bracket finding.")
                return parsed_json
            else:
                 logger.error(f"Could not find valid JSON structure in {description} output.")
                 return None
        except json.JSONDecodeError as final_e:
            logger.error(f"Final JSON parsing attempt failed for {description}: {final_e}. Giving up.")
            return None

# Ensure initialization happens somewhere before first use, e.g., in main.py
# initialize_vertex_ai() # Or call this explicitly early in your app lifecycle
