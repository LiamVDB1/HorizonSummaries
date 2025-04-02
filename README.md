# HorizonSummaries

**AI-powered content summarization for Jupiter DAO communications**

HorizonSummaries is a tool for automatically transcribing and summarizing Jupiter video content from various sources, including YouTube videos and Twitter (X) broadcasts. The tool downloads audio, generates accurate transcriptions using FalAI Whisper, preprocesses the text using AI to correct Jupiter-specific terminology and extract topics, and produces comprehensive summaries using Google's Vertex AI models.

## Features

-   **Multi-source video downloading** - Support for YouTube videos, Twitter (X) broadcasts (`x.com/i/broadcasts/...`), and direct `.m3u8` playlist URLs using `yt-dlp`.
-   **High-quality audio transcription** - Using FalAI Whisper with automatic audio splitting handled by the service (if applicable).
-   **AI-Powered Term Correction** - Uses Vertex AI to analyze transcripts against a list of known Jupiter terms, identifies likely errors, stores corrections in an SQLite database, and applies them for improved accuracy.
-   **AI-Powered Topic Extraction** - Uses Vertex AI to identify key topics and themes discussed in the transcript.
-   **AI-Powered Summarization** - Generates concise, engaging summaries using Google's Vertex AI (Gemini models recommended).
-   **Multiple content formats** - Supports specific prompt templates for Office Hours, Planetary Calls, Jup & Juice podcast episodes, etc.
-   **Customizable prompt templates** - Easily add or modify summarization prompts in the `data/prompts` directory.
-   **Persistent Term Corrections** - Learns and stores term corrections over time in a local SQLite database (`data/database/term_corrections.db`).

## Installation

### Prerequisites

-   Python 3.9 or later
-   `yt-dlp` installed and available in your system's PATH. ([Installation Guide](https://www.google.com/search?q=https://github.com/yt-dlp/yt-dlp%23installation))
-   Accounts for:
    -   [FalAI](https://fal.ai) for audio transcription API key/token.
    -   [Google Cloud](https://cloud.google.com) for Vertex AI access (Project ID and Credentials).

### Setup

1.  Clone this repository:
    ```bash
    git clone https://github.com/yourusername/HorizonSummaries.git
    cd HorizonSummaries
    ```

2.  Create a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use venv\Scripts\activate
    ```

3.  Install Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```

4.  Create a `.env` file based on the example:
    ```bash
    cp .env.example .env
    ```
    *(If `.env.example` doesn't exist, create `.env` manually)*

5.  Fill in your API credentials and configuration in the `.env` file:
    ```dotenv
    # .env file
    # Required
    FALAI_TOKEN=your_falai_token
    GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/google-cloud-credentials.json # Absolute path recommended
    GOOGLE_PROJECT_ID=your-google-project-id

    # Optional (Defaults are in src/config.py)
    GOOGLE_REGION=us-central1
    # You can override specific models if needed (defaults to Gemini Flash)
    # TERM_ANALYSIS_MODEL=gemini-1.5-pro-001
    # TOPIC_EXTRACTION_MODEL=gemini-1.5-pro-001
    # SUMMARIZATION_MODEL=gemini-1.5-pro-001
    ```
    **Important:** Ensure the `GOOGLE_APPLICATION_CREDENTIALS` path points to your downloaded Google Cloud service account key file.

6.  **Jupiter Terminology:** Review and update the list of known correct terms in `data/resources/jupiter_terms.json`. Add as many relevant terms as possible for better AI correction.
    ```json
    // data/resources/jupiter_terms.json
    {
      "terms": [
        "Jupiter", "JUP", "LFG Launchpad", "Perps", "Value Average",
        "Limit Order", "Swap", "Sanctum", "Wen", "Metropolis", "Zeus",
        "SharkyFi", "deBridge", "Solana", "Pyth", "Birdeye", "meteora",
        "JLP", "Working Group", "CEX", "DEX", "AMM", "Tinydancer"
        // Add more terms...
      ]
    }
    ```


## Usage

### Basic Usage

1.  Set environment variables for the run:
    ```bash
    export VIDEO_URL="https://x.com/i/broadcasts/1rmGPyBPApQJN" # Replace with your video URL
    export PROMPT_TYPE="planetary_call" # Options: 'office_hours', 'planetary_call', 'jup_and_juice' (or custom)
    # Ensure API keys are set in .env or as environment variables
    ```
    *(Alternatively, modify the default values directly in the `main()` function in `main.py` for quick tests)*

2.  Run the script from the project root directory:
    ```bash
    python main.py
    ```

3.  The script will execute the pipeline:
    -   Download the video and extract audio using `yt-dlp`.
    -   Transcribe the audio via FalAI Whisper.
    -   Clean the transcript.
    -   Analyze transcript for term errors using Vertex AI and known terms list.
    -   Update the term correction database (`data/database/term_corrections.db`).
    -   Apply corrections from the database.
    -   Extract topics using Vertex AI.
    -   Generate a summary using Vertex AI and the specified prompt template.
    -   Save raw transcript, processed transcript, and summary to the `data/output/{timestamp}_{title}/` directory.
    -   Clean up the temporary audio file.

### Custom Prompts

Create custom prompt templates by adding `{your_content_type}.txt` files to the `data/prompts` directory. The filename (without extension) is used as the `prompt_type`. Ensure your template includes placeholders like `{transcript}` and optionally `{topics}`.

## Directory Structure

```
HorizonSummaries/
├── data/
│   ├── database/           # Stores term_corrections.db (SQLite)
│   ├── prompts/            # Summarization prompt templates (*.txt)
│   ├── resources/          # Resource files (e.g., jupiter_terms.json)
│   └── output/             # Generated transcripts and summaries
├── src/
│   ├── database/           # SQLite database interaction (term_db.py)
│   ├── downloaders/        # Video downloading (common.py, twitter.py, youtube.py)
│   ├── llm/                # Vertex AI interactions (vertex_ai.py, term_analyzer.py, topic_extractor.py)
│   ├── preprocessing/      # Transcript processing (transcript_cleaner.py, term_correction.py)
│   ├── summarization/      # Prompt template loading (templates.py)
│   ├── transcription/      # FalAI Whisper interaction (fal_whisper.py)
│   ├── utils/              # Utility functions (file_handling.py, logger.py)
│   └── config.py           # Configuration settings
├── .env                    # API keys and environment variables (MUST BE CREATED)
├── .env.example            # Example environment file structure (Optional)
├── main.py                 # Main execution script
├── requirements.txt        # Python dependencies
└── README.md               # This documentation
```

## Extending the Project

-   **Adding New Content Types:** Create a new prompt template in `data/prompts/`. Use the filename as the `PROMPT_TYPE` when running `main.py`.
-   **Improving Term Correction:** Add more known terms to `data/resources/jupiter_terms.json`. The AI will use this list to improve its analysis. You can also manually inspect/edit the `data/database/term_corrections.db` file using an SQLite browser if needed, but the AI should manage it over time.
-   **Adding Downloaders:** Create new modules in `src/downloaders/` for other platforms, implement checker and downloader functions, and register them in `src/downloaders/common.py`.
-   **Changing AI Models:** Modify the default model names in `src/config.py` or override them using environment variables (`SUMMARIZATION_MODEL`, `TERM_ANALYSIS_MODEL`, `TOPIC_EXTRACTION_MODEL`).

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

-   [FalAI](https://fal.ai) for the Whisper API.
-   [Google Cloud](https://cloud.google.com) for Vertex AI (Gemini models).
-   [yt-dlp](https://github.com/yt-dlp/yt-dlp) for robust video/audio downloading.
-   The Jupiter community for inspiration and content.
