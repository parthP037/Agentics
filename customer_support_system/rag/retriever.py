"""
Small retrieval layer for the local knowledge base documents.

The project keeps retrieval lightweight: it chunks plain text files and scores
them with keyword overlap instead of relying on a separate vector database.
"""

import os
import re
from typing import List, Tuple

DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")

KNOWLEDGE_BASE_FILES = {
    "Company Policy":  os.path.join(DOCS_DIR, "company_policy.txt"),
    "Pricing Guide":   os.path.join(DOCS_DIR, "pricing_guide.txt"),
    "Technical Manual": os.path.join(DOCS_DIR, "technical_manual.txt"),
    "FAQ Document":    os.path.join(DOCS_DIR, "faq.txt"),
}


def load_documents() -> List[Tuple[str, str, str]]:
    """
    Read the knowledge base files and break them into reusable chunks.

    Returns:
        Tuples containing the document name, chunk ID, and chunk text.
    """
    chunks = []
    for doc_name, filepath in KNOWLEDGE_BASE_FILES.items():
        if not os.path.exists(filepath):
            continue
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        paragraphs = [p.strip() for p in content.split("\n\n") if len(p.strip()) > 30]
        for i, para in enumerate(paragraphs):
            chunks.append((doc_name, f"{doc_name}_{i}", para))
    return chunks


_CHUNKS = load_documents()


def _simple_score(query: str, text: str) -> float:
    """
    Give a simple relevance score to one text chunk for the query.

    Matching is case-insensitive and gives a small boost when a query term
    appears more than once.
    """
    query_words = set(re.findall(r'\b\w{3,}\b', query.lower()))
    text_lower = text.lower()

    score = 0.0
    for word in query_words:
        count = text_lower.count(word)
        if count > 0:
            score += 1 + 0.1 * (count - 1)
    return score


def retrieve_context(query: str, top_k: int = 3, min_score: float = 0.5) -> str:
    """
    Find the most relevant knowledge base passages for a query.

    Args:
        query: Customer's message.
        top_k: Number of chunks to return.
        min_score: Lowest score worth including.

    Returns:
        A formatted context block for the support agent prompt.
    """
    scored = []
    for doc_name, chunk_id, chunk_text in _CHUNKS:
        score = _simple_score(query, chunk_text)
        if score >= min_score:
            scored.append((score, doc_name, chunk_text))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_chunks = scored[:top_k]

    if not top_chunks:
        return "No relevant context found in the knowledge base."

    parts = []
    for score, doc_name, chunk_text in top_chunks:
        parts.append(f"[Source: {doc_name}]\n{chunk_text}")

    return "\n\n---\n\n".join(parts)


def retrieve_context_by_intent(query: str, intent: str) -> str:
    """
    Retrieve context with a small preference for intent-specific documents.

    Args:
        query: Customer's message.
        intent: Classified support intent.

    Returns:
        A formatted context block for the support agent prompt.
    """
    intent_doc_map = {
        "Sales":     ["Pricing Guide", "FAQ Document"],
        "Technical": ["Technical Manual", "FAQ Document"],
        "Billing":   ["Company Policy", "FAQ Document"],
        "Account":   ["Technical Manual", "FAQ Document"],
        "Memory":    [],  
    }

    preferred_sources = intent_doc_map.get(intent, [])

    scored = []
    for doc_name, chunk_id, chunk_text in _CHUNKS:
        score = _simple_score(query, chunk_text)
        if doc_name in preferred_sources:
            score *= 1.5
        if score >= 0.3:
            scored.append((score, doc_name, chunk_text))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_chunks = scored[:4]

    if not top_chunks:
        return "No relevant context found in the knowledge base."

    parts = []
    for score, doc_name, chunk_text in top_chunks:
        parts.append(f"[Source: {doc_name}]\n{chunk_text}")

    return "\n\n---\n\n".join(parts)
