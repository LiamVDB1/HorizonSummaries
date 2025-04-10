"""
Prompt templates for summarization tasks.
"""

import os
import logging
from typing import Dict

from src.config import Config
from src.utils.file_handling import read_file

logger = logging.getLogger("horizon_summaries")

# Default templates for different content types
DEFAULT_TEMPLATES = {
    "office_hours": """
Summarize the latest Office Hours transcript in a fun, energetic, and engaging way. 
Focus on key topics discussed, decisions made, and any exciting announcements or updates, while capturing the casual, humorous tone of the conversation. Be sure to use **emojis** to make the summary lively and interactive! 
Keep it concise but **comprehensive**, ensuring that **ALL relevant elements and moments** from the conversation are included.

**Working Group Updates**: Make sure to provide updates from each working group, capturing their key announcements, decisions, and upcoming plans. Format the output as bullet points under each working group name, like this:
"
Working Group Updates

	•	Uplink Working Group
		•	[Key update or decision made]
		•	[Next steps or upcoming plans]
	•	DAO Working Group
		•	[Key update or decision made]
		•	[Next steps or upcoming plans]
"

Write the thread as an external person (no "We did this")
Highlight any funny moments, inside jokes, and interesting ideas discussed, especially those that reflect the community spirit.
Ensure the summary feels accessible to both newcomers and long-term community members. Use Jupiter-specific lingo and community phrases where applicable!

Key topics from the transcript: {TOPICS}

Office Hours Context:
"Jupiter's Office Hours are weekly sessions hosted by the Core Working Group (CWG) and various other working groups. These meetings provide an open platform for community members to discuss topics related to the DAO, governance, ongoing working group projects, and broader Web3 initiatives. It's an excellent opportunity for members to ask questions, provide feedback, and gain insights into the latest developments in the Jupiter ecosystem. Additionally, specific sessions are often allocated for catdets and other contributors to present their own initiatives and engage with the community on a more personal level"

Jupiter Context:
"Jupiter is a decentralized finance (DeFi) platform built on Solana, initially known as the top aggregator for token swaps. Beyond its roots in trading, Jupiter has grown into a dynamic ecosystem that offers perpetual trading, liquidity provision, and governance mechanisms. At its heart is the Jupiverse, which integrates all aspects of the platform into a cohesive community-driven environment.

The Jupiverse refers to the collective of users, working groups, contributors, and developers working together to shape Jupiter's future. DAO governance is a crucial element, where $JUP holders vote on decisions ranging from project launches to strategic changes. The working groups, such as the Core and Uplink groups, handle vital aspects like community management, ecosystem token lists, and the LFG launchpad process ￼ ￼. These groups are the engines that power Jupiter's growth, facilitating everything from grant programs to token curations.

The LFG Launchpad empowers the community to decide which new projects within the Solana ecosystem receive support, creating a continuous cycle of innovation ￼. Through these initiatives, the Jupiverse embodies a thriving DeFi ecosystem built on collaboration, transparency, and decentralized governance.

With this comprehensive framework, Jupiter has become a central hub of decentralized finance, fostering community participation while advancing DeFi on Solana"

{JUPITER_CONTEXT}

{TOPICS}

**Transcript:**
{TRANSCRIPT}
""",

    "planetary_call": """
Summarize the latest Jupiter Planetary Call transcript in a clear, engaging, and informative manner.
Focus on the key announcements, discussions, decisions, and community initiatives mentioned in the call.
Make sure to include relevant context and explanations where needed, especially for technical topics.

**Style Guidelines:**
- Use a community-focused tone that's enthusiastic but professional
- Include emojis 🪐 to highlight key points and maintain engagement
- Structure the summary with clear headings and bullet points
- Aim for a concise yet comprehensive overview
- Include any calls to action or upcoming events mentioned

**Key Sections to Include:**
1. **Call Overview** - A brief introduction and the main themes of the call
2. **Project Updates** - Technical developments and roadmap progress
3. **Governance Highlights** - DAO decisions, proposals, and voting information
4. **Community Initiatives** - Community-led projects and contributions
5. **Q&A Highlights** - Notable questions and answers from the community
6. **Coming Up** - Upcoming events, votes, or initiatives

The summary should be informative both for those who missed the call and those who attended but want a recap of the main points.

Key topics from the transcript: {TOPICS}

**Transcript:**
{TRANSCRIPT}
""",

    "jup_and_juice": """
Summarize the latest Jup & Juice podcast episode in a lively, engaging style that captures the casual, conversational nature of the podcast. 
Use a mix of informative content and entertainment value, highlighting the key discussion points while preserving the podcast's distinctive personality and humor.

**Style Guidelines:**
- Keep the tone light, friendly, and conversational
- Use emojis 🧃 to add visual interest and highlight key points
- Include direct quotes or memorable moments from hosts/guests
- Maintain the podcast's signature blend of educational content and entertainment
- Organize with clear sections but maintain a flowing narrative style

**Key Sections to Include:**
1. **Episode Introduction** - Episode number, title, and guest(s) if any
2. **Main Discussion Topics** - The primary themes and subjects explored 
3. **Jupiter Ecosystem Updates** - Any news or developments discussed about Jupiter
4. **Guest Insights** - If applicable, key perspectives or expertise shared by guests
5. **Community Highlights** - Any mentions of community contributions or initiatives
6. **Key Takeaways** - The most important points or conclusions

Format the summary to be engaging for both regular listeners who want a recap and potential new listeners who might discover the podcast through this summary.

Key topics from the transcript: {TOPICS}

**Transcript:**
{TRANSCRIPT}
"""
}


def save_default_templates():
    """
    Save default templates to files if they don't exist.
    """
    for template_type, template_content in DEFAULT_TEMPLATES.items():
        template_path = os.path.join(Config.PROMPTS_DIR, f"{template_type}.txt")

        # Check if file already exists
        if not os.path.exists(template_path):
            # Ensure directory exists
            os.makedirs(os.path.dirname(template_path), exist_ok=True)

            # Save template
            with open(template_path, 'w', encoding='utf-8') as f:
                f.write(template_content)

            logger.info(f"Saved default {template_type} template to {template_path}")


def get_prompt_template(template_type: str) -> str:
    """
    Get a prompt template for summarization.

    Args:
        template_type (str): Type of template (e.g., 'office_hours', 'planetary_call')

    Returns:
        str: Prompt template
    """
    # Ensure default templates are saved
    save_default_templates()

    template_path = os.path.join(Config.PROMPTS_DIR, f"{template_type}.txt")

    try:
        # Try to load template from file
        template = read_file(template_path)
        logger.info(f"Loaded {template_type} template from {template_path}")
        return template

    except FileNotFoundError:
        # If not found, use default template
        logger.warning(f"Template file {template_path} not found, using default")

        if template_type in DEFAULT_TEMPLATES:
            return DEFAULT_TEMPLATES[template_type]
        else:
            # If template type not recognized, use a generic template
            logger.warning(f"Unknown template type: {template_type}, using generic template")
            return DEFAULT_TEMPLATES["office_hours"]  # Use office_hours as fallback


def list_available_templates() -> Dict[str, str]:
    """
    List all available templates with their descriptions.

    Returns:
        Dict[str, str]: Dictionary of template name -> description
    """
    templates = {
        "office_hours": "Summary template for Jupiter Office Hours",
        "planetary_call": "Summary template for Jupiter Planetary Calls",
        "jup_and_juice": "Summary template for Jup & Juice podcast episodes"
    }

    # Add any custom templates found in the prompts directory
    prompts_dir = Config.PROMPTS_DIR
    if os.path.exists(prompts_dir):
        for filename in os.listdir(prompts_dir):
            if filename.endswith('.txt'):
                template_name = os.path.splitext(filename)[0]
                if template_name not in templates:
                    templates[template_name] = f"Custom template: {template_name}"

    return templates