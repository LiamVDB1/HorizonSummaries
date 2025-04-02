# HorizonSummaries

**AI-powered content summarization for Jupiter DAO communications**

HorizonSummaries is a tool for automatically transcribing and summarizing Jupiter video content from various sources, including YouTube videos and Twitter broadcasts. The tool downloads audio, generates accurate transcriptions using FalAI Whisper, preprocesses the text to correct Jupiter-specific terminology, and produces comprehensive summaries using Google's Vertex AI models.

## Features

- **Multi-source video downloading** - Support for YouTube videos, Twitter broadcasts, and direct m3u8 playlist URLs
- **High-quality audio transcription** - Using FalAI Whisper with automatic audio splitting for large files
- **Jupiter-specific text processing** - Automatically corrects terminology unique to Jupiter ecosystem
- **Topic extraction** - Identifies key topics and themes from transcripts
- **AI-powered summarization** - Generates concise, engaging summaries using Google's Vertex AI
- **Multiple content formats** - Supports Office Hours, Planetary Calls, and Jup & Juice podcast episodes
- **Customizable prompt templates** - Easily add or modify summarization prompts

## Installation

### Prerequisites

- Python 3.9 or later
- Accounts for:
  - [FalAI](https://fal.ai) for audio transcription
  - [Google Cloud](https://cloud.google.com) for Vertex AI access

### Setup

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/HorizonSummaries.git
   cd HorizonSummaries
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file based on the example:
   ```bash
   cp .env.example .env
   ```

5. Fill in your API credentials in the `.env` file:
   ```
   FALAI_TOKEN=your_falai_token
   GOOGLE_APPLICATION_CREDENTIALS=path/to/your/google-credentials.json
   GOOGLE_PROJECT_ID=your-google-project-id
   GOOGLE_REGION=us-central1
   ```

## Usage

### Basic Usage

1. Open `main.py` and update the configuration variables:
   ```python
   # Configure these variables for each run
   video_url = "https://youtube.com/watch?v=your_video_id"  # Replace with your video URL
   prompt_type = "office_hours"  # Options: 'office_hours', 'planetary_call', 'jup_and_juice'
   model_name = None  # Will use default from Config if None
   ```

2. Run the script:
   ```bash
   python main.py
   ```

3. The script will:
   - Download the video and extract audio
   - Transcribe the audio
   - Clean and process the transcript
   - Generate a summary
   - Save all outputs to the `data/output` directory

### Custom Prompts

You can create custom prompt templates by adding text files to the `data/prompts` directory. The filename (without extension) will be the prompt type identifier.

## Directory Structure

```
HorizonSummaries/
├── data/
│   ├── prompts/            # Summarization prompt templates
│   ├── resources/          # Resource files like Jupiter terminology
│   └── output/             # Generated transcripts and summaries
├── src/
│   ├── downloaders/        # Video downloading utilities
│   ├── transcription/      # Audio transcription with FalAI
│   ├── preprocessing/      # Transcript cleaning and enhancement
│   ├── summarization/      # AI summarization with Vertex AI
│   ├── utils/              # Utility functions
│   └── config.py           # Configuration settings
├── main.py                 # Main execution script
├── requirements.txt        # Dependencies
└── README.md               # Documentation
```

## Extending the Project

### Adding New Content Types

1. Create a new prompt template in `data/prompts/{your_content_type}.txt`
2. Update the prompt template description in `src/summarization/templates.py`

### Improving Term Correction

Edit the Jupiter terms dictionary in `data/resources/jupiter_terms.json` to add new terms or corrections.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [FalAI](https://fal.ai) for providing the Whisper API
- [Google Cloud](https://cloud.google.com) for Vertex AI access
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for video downloading capabilities
- The Jupiter community for inspiration and support