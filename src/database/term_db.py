# src/database/term_db.py
"""
Handles SQLite database operations for storing and retrieving
term corrections identified by the LLM.
"""

import sqlite3
import logging
from typing import List, Tuple, Dict, Optional, Any
from pathlib import Path

from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

DATABASE_PATH = Config.TERM_DATABASE_FILE


def _get_connection() -> Optional[sqlite3.Connection]:
    """Establishes a connection to the SQLite database."""
    try:
        # Ensure the directory exists
        Config.DATABASE_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DATABASE_PATH, timeout=10)  # Add timeout
        conn.row_factory = sqlite3.Row  # Return rows as dict-like objects
        logger.debug(f"Database connection established to {DATABASE_PATH}")
        return conn
    except sqlite3.Error as e:
        logger.error(f"Error connecting to database {DATABASE_PATH}: {e}", exc_info=True)
        return None


def initialize_database():
    """Creates the term_corrections table if it doesn't exist."""
    logger.info(f"Initializing database schema at {DATABASE_PATH}...")
    conn = _get_connection()
    if conn is None:
        return  # Error already logged

    try:
        with conn:  # Use context manager for automatic commit/rollback
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS term_corrections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incorrect_term TEXT NOT NULL UNIQUE,
                    correct_term TEXT NOT NULL,
                    confidence FLOAT DEFAULT 1.0,
                    reasoning TEXT,
                    correction_type TEXT DEFAULT 'term', -- 'term', 'person', 'acronym'
                    source TEXT DEFAULT 'llm_identified', -- e.g., 'llm_identified', 'manual'
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Optional: Create an index for faster lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_incorrect_term ON term_corrections (incorrect_term);
            """)
            # Create index for correction_type for filtering
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_correction_type ON term_corrections (correction_type);
            """)
            logger.info("Database table 'term_corrections' initialized successfully.")
    except sqlite3.Error as e:
        logger.error(f"Error initializing database table: {e}", exc_info=True)
    finally:
        conn.close()
        logger.debug("Database connection closed after initialization.")


def add_term_correction(
        incorrect_term: str,
        correct_term: str,
        confidence: float = 1.0,
        reasoning: Optional[str] = None,
        correction_type: str = 'term',
        source: str = 'llm_identified'
):
    """
    Adds a new term correction pair to the database or updates the timestamp if it exists.

    Args:
        incorrect_term (str): The misspelled or incorrect term found.
        correct_term (str): The correct term.
        confidence (float): Confidence score between 0.0 and 1.0.
        reasoning (str, optional): Explanation for the correction.
        correction_type (str): Type of correction ('term', 'person', 'acronym').
        source (str): Where this correction originated from.
    """
    if not incorrect_term or not correct_term:
        logger.warning("Attempted to add empty term correction, skipping.")
        return

    conn = _get_connection()
    if conn is None: return

    try:
        with conn:
            cursor = conn.cursor()
            # Use INSERT OR REPLACE (or INSERT ... ON CONFLICT DO UPDATE) to handle uniqueness
            # This will replace the existing row if incorrect_term matches
            cursor.execute("""
                INSERT INTO term_corrections (
                    incorrect_term, correct_term, confidence, reasoning, 
                    correction_type, source, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(incorrect_term) DO UPDATE SET
                    correct_term = excluded.correct_term,
                    confidence = excluded.confidence,
                    reasoning = excluded.reasoning,
                    correction_type = excluded.correction_type,
                    source = excluded.source,
                    updated_at = CURRENT_TIMESTAMP;
            """, (incorrect_term, correct_term, confidence, reasoning, correction_type, source))
            logger.debug(f"Added/Updated term correction: '{incorrect_term}' -> '{correct_term}'")
    except sqlite3.Error as e:
        logger.error(f"Error adding/updating term correction ('{incorrect_term}' -> '{correct_term}'): {e}",
                     exc_info=True)
    finally:
        conn.close()


def add_multiple_term_corrections(
        corrections: Dict[str, Any],
        source: str = 'llm_identified'
):
    """
    Adds multiple term corrections from a dictionary.

    Args:
        corrections (Dict[str, Any]): Dictionary where:
            - Key is the incorrect term
            - Value is either a string (correct term) or dict with 'term', 'confidence', etc.
        source (str): Source of these corrections.
    """
    if not corrections:
        return

    conn = _get_connection()
    if conn is None: return

    data_to_insert = []
    for incorrect, correction_data in corrections.items():
        if not incorrect:
            continue

        # Handle two formats: simple string or detailed dict
        if isinstance(correction_data, str):
            # Simple format: {"incorrect": "correct"}
            correct = correction_data
            confidence = 1.0
            reasoning = None
            correction_type = 'term'
        elif isinstance(correction_data, dict):
            # Detailed format: {"incorrect": {"term": "correct", "confidence": 0.9, ...}}
            correct = correction_data.get('term', '')
            confidence = correction_data.get('confidence', 1.0)
            reasoning = correction_data.get('reasoning')
            correction_type = correction_data.get('correction_type', 'term')
        else:
            logger.warning(f"Invalid correction data format for '{incorrect}': {correction_data}")
            continue

        if not correct:
            continue

        data_to_insert.append(
            (incorrect, correct, confidence, reasoning, correction_type, source)
        )

    if not data_to_insert:
        logger.warning("No valid correction pairs provided to add_multiple_term_corrections.")
        conn.close()
        return

    try:
        with conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT INTO term_corrections (
                    incorrect_term, correct_term, confidence, reasoning, 
                    correction_type, source, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(incorrect_term) DO UPDATE SET
                    correct_term = excluded.correct_term,
                    confidence = excluded.confidence,
                    reasoning = excluded.reasoning,
                    correction_type = excluded.correction_type,
                    source = excluded.source,
                    updated_at = CURRENT_TIMESTAMP;
            """, data_to_insert)
            logger.info(f"Added/Updated {len(data_to_insert)} term corrections.")
    except sqlite3.Error as e:
        logger.error(f"Error adding multiple term corrections: {e}", exc_info=True)
    finally:
        conn.close()


def get_all_term_corrections(
        min_confidence: float = 0.0,
        correction_types: Optional[List[str]] = None
) -> Dict[str, str]:
    """
    Retrieves all term corrections from the database that meet the criteria.

    Args:
        min_confidence (float): Minimum confidence threshold (0.0-1.0)
        correction_types (List[str], optional): List of correction types to include
                                              (e.g., ['term', 'person'])

    Returns:
        Dict[str, str]: A dictionary mapping {incorrect_term: correct_term}.
    """
    corrections = {}
    conn = _get_connection()
    if conn is None: return corrections  # Return empty dict on connection error

    try:
        with conn:
            cursor = conn.cursor()

            # Build the query based on parameters
            query = """
                SELECT incorrect_term, correct_term 
                FROM term_corrections 
                WHERE confidence >= ?
            """
            params = [min_confidence]

            # Add correction_types filter if provided
            if correction_types:
                placeholders = ','.join(['?'] * len(correction_types))
                query += f" AND correction_type IN ({placeholders})"
                params.extend(correction_types)

            # Order by length descending helps replace longer phrases first
            query += " ORDER BY length(incorrect_term) DESC"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            for row in rows:
                corrections[row['incorrect_term']] = row['correct_term']

            logger.info(f"Retrieved {len(corrections)} term corrections from database.")
    except sqlite3.Error as e:
        logger.error(f"Error retrieving term corrections: {e}", exc_info=True)
    finally:
        conn.close()
        logger.debug("Database connection closed after retrieving corrections.")
    return corrections


def get_term_corrections_with_metadata(
        min_confidence: float = 0.0,
        correction_types: Optional[List[str]] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Retrieves term corrections with all metadata.

    Args:
        min_confidence (float): Minimum confidence threshold (0.0-1.0)
        correction_types (List[str], optional): List of correction types to include

    Returns:
        Dict[str, Dict[str, Any]]: A dictionary mapping
            {incorrect_term: {term, confidence, reasoning, etc.}}
    """
    corrections = {}
    conn = _get_connection()
    if conn is None: return corrections

    try:
        with conn:
            cursor = conn.cursor()

            # Build the query based on parameters
            query = """
                SELECT incorrect_term, correct_term, confidence, reasoning, 
                       correction_type, source, created_at, updated_at
                FROM term_corrections 
                WHERE confidence >= ?
            """
            params = [min_confidence]

            # Add correction_types filter if provided
            if correction_types:
                placeholders = ','.join(['?'] * len(correction_types))
                query += f" AND correction_type IN ({placeholders})"
                params.extend(correction_types)

            # Order by length descending
            query += " ORDER BY length(incorrect_term) DESC"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            for row in rows:
                corrections[row['incorrect_term']] = {
                    'term': row['correct_term'],
                    'confidence': row['confidence'],
                    'reasoning': row['reasoning'],
                    'correction_type': row['correction_type'],
                    'source': row['source'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                }

            logger.info(f"Retrieved {len(corrections)} detailed term corrections from database.")
    except sqlite3.Error as e:
        logger.error(f"Error retrieving detailed term corrections: {e}", exc_info=True)
    finally:
        conn.close()
    return corrections


# Ensure the database is initialized when the module is loaded
# This might run multiple times if the module is reloaded, but the CREATE TABLE IF NOT EXISTS handles it.
initialize_database()