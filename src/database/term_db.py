# src/database/term_db.py
"""
Handles SQLite database operations for storing and retrieving
term corrections identified by the LLM.
"""

import sqlite3
import logging
from typing import List, Tuple, Dict, Optional
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
        conn = sqlite3.connect(DATABASE_PATH, timeout=10) # Add timeout
        conn.row_factory = sqlite3.Row # Return rows as dict-like objects
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
        return # Error already logged

    try:
        with conn: # Use context manager for automatic commit/rollback
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS term_corrections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incorrect_term TEXT NOT NULL UNIQUE,
                    correct_term TEXT NOT NULL,
                    source TEXT DEFAULT 'llm_identified', -- e.g., 'llm_identified', 'manual'
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    -- Optional: Add confidence score, frequency, last_seen etc.
                )
            """)
            # Optional: Create an index for faster lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_incorrect_term ON term_corrections (incorrect_term);
            """)
            logger.info("Database table 'term_corrections' initialized successfully.")
    except sqlite3.Error as e:
        logger.error(f"Error initializing database table: {e}", exc_info=True)
    finally:
        conn.close()
        logger.debug("Database connection closed after initialization.")


def add_term_correction(incorrect_term: str, correct_term: str, source: str = 'llm_identified'):
    """
    Adds a new term correction pair to the database or updates the timestamp if it exists.

    Args:
        incorrect_term (str): The misspelled or incorrect term found.
        correct_term (str): The correct term.
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
                INSERT INTO term_corrections (incorrect_term, correct_term, source, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(incorrect_term) DO UPDATE SET
                    correct_term = excluded.correct_term,
                    source = excluded.source,
                    updated_at = CURRENT_TIMESTAMP;
            """, (incorrect_term, correct_term, source))
            logger.debug(f"Added/Updated term correction: '{incorrect_term}' -> '{correct_term}'")
    except sqlite3.Error as e:
        logger.error(f"Error adding/updating term correction ('{incorrect_term}' -> '{correct_term}'): {e}", exc_info=True)
    finally:
        conn.close()

def add_multiple_term_corrections(corrections: Dict[str, str], source: str = 'llm_identified'):
    """
    Adds multiple term corrections from a dictionary.

    Args:
        corrections (Dict[str, str]): Dictionary of {incorrect: correct}.
        source (str): Source of these corrections.
    """
    if not corrections:
        return

    conn = _get_connection()
    if conn is None: return

    data_to_insert = [
        (incorrect, correct, source)
        for incorrect, correct in corrections.items() if incorrect and correct
    ]

    if not data_to_insert:
        logger.warning("No valid correction pairs provided to add_multiple_term_corrections.")
        conn.close()
        return

    try:
        with conn:
            cursor = conn.cursor()
            # Use INSERT OR REPLACE for batch insertion
            # Note: This might be less efficient than ON CONFLICT DO UPDATE for large batches with many conflicts
            cursor.executemany("""
                INSERT INTO term_corrections (incorrect_term, correct_term, source, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(incorrect_term) DO UPDATE SET
                    correct_term = excluded.correct_term,
                    source = excluded.source,
                    updated_at = CURRENT_TIMESTAMP;
            """, data_to_insert)
            logger.info(f"Added/Updated {len(data_to_insert)} term corrections.")
    except sqlite3.Error as e:
        logger.error(f"Error adding multiple term corrections: {e}", exc_info=True)
    finally:
        conn.close()

def get_all_term_corrections() -> Dict[str, str]:
    """
    Retrieves all term corrections from the database.

    Returns:
        Dict[str, str]: A dictionary mapping {incorrect_term: correct_term}.
    """
    corrections = {}
    conn = _get_connection()
    if conn is None: return corrections # Return empty dict on connection error

    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT incorrect_term, correct_term FROM term_corrections ORDER BY length(incorrect_term) DESC")
            rows = cursor.fetchall()
            # Order by length descending helps replace longer phrases first (e.g., "Jupiter perp" before "perp")
            for row in rows:
                corrections[row['incorrect_term']] = row['correct_term']
            logger.info(f"Retrieved {len(corrections)} term corrections from database.")
    except sqlite3.Error as e:
        logger.error(f"Error retrieving term corrections: {e}", exc_info=True)
    finally:
        conn.close()
        logger.debug("Database connection closed after retrieving corrections.")
    return corrections

# Ensure the database is initialized when the module is loaded
# This might run multiple times if the module is reloaded, but the CREATE TABLE IF NOT EXISTS handles it.
initialize_database()
