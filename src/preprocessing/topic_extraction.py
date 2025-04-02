"""
Functions for extracting main topics from transcripts.
"""

import re
import logging
from typing import List, Dict
from collections import Counter

from src.preprocessing.term_correction import load_jupiter_terms

logger = logging.getLogger("horizon_summaries")

# Working groups relevant to Jupiter DAO
WORKING_GROUPS = [
    "Core Working Group", "CWG",
    "Uplink Working Group", "Uplink",
    "Catdet Working Group", "CAWG", "Catdets",
    "Jup & Juice", "Jup and Juice",
    "AI Working Group", "AIWG", "Jupiter Horizon"
]

# Jupiter products and features
JUPITER_PRODUCTS = [
    "Jupiter Swap", "Jupiter Perpetuals", "Perpetuals", "Perps",
    "JupSOL", "LFG Launchpad", "LFG",
    "Limit Orders", "DCA", "Dollar Cost Averaging",
    "ASR", "Active Staking Rewards", "Jupiter Mobile"
]

# Governance related terms
GOVERNANCE_TERMS = [
    "DAO", "governance", "proposal", "vote", "voting", "quorum",
    "token", "JUP token", "staking", "grant", "bounty"
]


def extract_topics(transcript: str) -> List[str]:
    """
    Extract main topics from a transcript.

    Args:
        transcript (str): The transcript text

    Returns:
        List[str]: List of main topics
    """
    logger.info("Extracting main topics from transcript")

    # 1. Use keyword frequency analysis
    topics_from_keywords = extract_topics_from_keywords(transcript)

    # 2. Check for specific working group mentions
    working_group_topics = extract_working_group_topics(transcript)

    # 3. Extract topics from headers or section transitions
    section_topics = extract_section_topics(transcript)

    # Combine all topics and remove duplicates
    all_topics = list(set(topics_from_keywords + working_group_topics + section_topics))

    logger.info(f"Extracted {len(all_topics)} topics")
    return all_topics


def extract_topics_from_keywords(transcript: str) -> List[str]:
    """
    Extract topics based on keyword frequency.

    Args:
        transcript (str): The transcript text

    Returns:
        List[str]: List of topics from keyword analysis
    """
    # Get Jupiter terms for recognition
    jupiter_terms = load_jupiter_terms()

    # Combined list of important terms to look for
    important_terms = list(jupiter_terms.values()) + WORKING_GROUPS + JUPITER_PRODUCTS + GOVERNANCE_TERMS

    # Create regex pattern to find these terms
    pattern = r'\b(?:' + '|'.join(map(re.escape, important_terms)) + r')\b'

    # Find all matches
    matches = re.findall(pattern, transcript, re.IGNORECASE)

    # Count frequency
    counter = Counter(map(str.lower, matches))

    # Filter to keep only terms that appear multiple times
    frequent_terms = [term for term, count in counter.items() if count >= 2]

    # Convert to proper case using the original terms as reference
    term_case_map = {term.lower(): term for term in important_terms}

    # Return the frequent terms with proper casing
    return [term_case_map.get(term, term.title()) for term in frequent_terms]


def extract_working_group_topics(transcript: str) -> List[str]:
    """
    Extract topics related to working groups.

    Args:
        transcript (str): The transcript text

    Returns:
        List[str]: List of working group related topics
    """
    topics = []

    # Check for mentions of working groups
    for group in WORKING_GROUPS:
        if re.search(r'\b' + re.escape(group) + r'\b', transcript, re.IGNORECASE):
            topics.append(group)

    # Extract specific activity topics for each working group
    for group in set(topics):
        # Look for sentences mentioning the group and extract key activities
        pattern = r'[^.!?]*\b' + re.escape(group) + r'\b[^.!?]*[.!?]'
        mentions = re.findall(pattern, transcript, re.IGNORECASE)

        for mention in mentions:
            # Check for activity verbs
            activities = re.findall(r'\b(?:working on|planning|announced|updated|released|launched)\b[^.!?]+', mention,
                                    re.IGNORECASE)

            for activity in activities:
                # Format as "[Group] [Activity]"
                topics.append(f"{group} {activity.strip()}")

    return topics


def extract_section_topics(transcript: str) -> List[str]:
    """
    Extract topics from section headers or transitions.

    Args:
        transcript (str): The transcript text

    Returns:
        List[str]: List of section topics
    """
    topics = []

    # Look for explicit section headers or transitions
    section_patterns = [
        r'(?:Moving on to|Next up|Let\'s talk about|Turning to|Shifting to|Now about|Discussing)\s+([^.!?]+)',
        r'(?:First|Second|Third|Next|Finally),\s+([^.!?]+)',
        r'Topic\s*(?:\d+)?:\s*([^.!?]+)'
    ]

    for pattern in section_patterns:
        sections = re.findall(pattern, transcript, re.IGNORECASE)
        for section in sections:
            # Clean up the section title
            clean_section = re.sub(r'\b(?:we have|we are|let\'s|about)\b', '', section, flags=re.IGNORECASE)
            clean_section = clean_section.strip()

            if len(clean_section) > 3:  # Avoid very short topics
                topics.append(clean_section)

    return topics


def categorize_topics(topics: List[str]) -> Dict[str, List[str]]:
    """
    Categorize topics into groups.

    Args:
        topics (List[str]): List of topics

    Returns:
        Dict[str, List[str]]: Dictionary of category -> list of topics
    """
    categories = {
        "Working Groups": [],
        "Products & Features": [],
        "Governance": [],
        "Community": [],
        "Other": []
    }

    for topic in topics:
        if any(group.lower() in topic.lower() for group in WORKING_GROUPS):
            categories["Working Groups"].append(topic)
        elif any(product.lower() in topic.lower() for product in JUPITER_PRODUCTS):
            categories["Products & Features"].append(topic)
        elif any(term.lower() in topic.lower() for term in GOVERNANCE_TERMS):
            categories["Governance"].append(topic)
        elif any(term.lower() in topic.lower() for term in
                 ["community", "member", "user", "event", "twitter", "social"]):
            categories["Community"].append(topic)
        else:
            categories["Other"].append(topic)

    # Remove empty categories
    return {k: v for k, v in categories.items() if v}