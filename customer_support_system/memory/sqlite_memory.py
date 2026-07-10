"""
SQLite helpers for storing customer conversation history.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict

DB_PATH = os.path.join(os.path.dirname(__file__), "memory.db")


def init_db():
    """Create the conversation history table if the database is new."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversation_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT    NOT NULL,
            customer_name TEXT,
            role        TEXT    NOT NULL,
            message     TEXT    NOT NULL,
            intent      TEXT,
            timestamp   TEXT    NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_interaction(
    customer_id: str,
    role: str,
    message: str,
    intent: str = None,
    customer_name: str = None
):
    """
    Save one user or assistant message to the conversation history.

    Args:
        customer_id: Stable ID for the customer.
        role: Message role, usually "user" or "assistant".
        message: Text to store.
        intent: Classified intent for the turn, if available.
        customer_name: Customer name, if we know it.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO conversation_history (customer_id, customer_name, role, message, intent, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (customer_id, customer_name, role, message, intent, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_conversation_history(customer_id: str, limit: int = 10) -> List[Dict]:
    """
    Get the latest saved messages for a customer.

    Args:
        customer_id: Stable ID for the customer.
        limit: Maximum number of messages to load.

    Returns:
        Message dictionaries ordered from oldest to newest.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT role, message, intent, timestamp, customer_name
        FROM conversation_history
        WHERE customer_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (customer_id, limit))
    rows = cursor.fetchall()
    conn.close()

    history = []
    for row in reversed(rows):
        history.append({
            "role": row[0],
            "message": row[1],
            "intent": row[2],
            "timestamp": row[3],
            "customer_name": row[4]
        })
    return history


def get_customer_name(customer_id: str) -> str:
    """Find the most recently saved name for a customer."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT customer_name FROM conversation_history
        WHERE customer_id = ? AND customer_name IS NOT NULL
        ORDER BY timestamp DESC LIMIT 1
    """, (customer_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def format_history_for_prompt(history: List[Dict]) -> str:
    """Turn saved history into a compact block for prompts."""
    if not history:
        return "No previous conversation history."

    formatted = []
    for item in history:
        ts = item["timestamp"][:19].replace("T", " ")
        intent_str = f" [{item['intent']}]" if item["intent"] else ""
        formatted.append(f"[{ts}]{intent_str} {item['role'].upper()}: {item['message']}")

    return "\n".join(formatted)


def clear_customer_history(customer_id: str):
    """Clear saved messages for one customer."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM conversation_history WHERE customer_id = ?", (customer_id,))
    conn.commit()
    conn.close()


init_db()
