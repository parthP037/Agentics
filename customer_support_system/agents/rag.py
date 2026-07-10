"""
agents/rag.py
Simple keyword-based RAG pipeline — no API keys or embeddings required.
Retrieves relevant paragraphs from knowledge base documents.
"""

import os
import re

KB_DIR = os.path.join(os.path.dirname(__file__), "..", "knowledge_base")

# Map each document to a friendly name
DOCUMENTS = {
    "pricing_guide.txt":  "Pricing Guide",
    "company_policy.txt": "Company Policy",
    "technical_manual.txt": "Technical Manual",
    "faq.txt":            "FAQ",
}

# Which docs to search per department
DEPT_DOCS = {
    "Sales":     ["pricing_guide.txt", "faq.txt"],
    "Technical": ["technical_manual.txt", "faq.txt"],
    "Billing":   ["company_policy.txt", "faq.txt"],
    "Account":   ["faq.txt", "company_policy.txt"],
    "General":   ["faq.txt", "pricing_guide.txt", "company_policy.txt", "technical_manual.txt"],
}


def _load_document(filename: str) -> str:
    path = os.path.join(KB_DIR, filename)
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _split_paragraphs(text: str) -> list[str]:
    """Split text into meaningful paragraphs/sections."""
    paragraphs = re.split(r"\n{2,}", text.strip())
    return [p.strip() for p in paragraphs if len(p.strip()) > 30]


def _score_paragraph(paragraph: str, keywords: list[str]) -> int:
    """Score a paragraph by how many keywords it contains (case-insensitive)."""
    lower = paragraph.lower()
    return sum(1 for kw in keywords if kw.lower() in lower)


def retrieve(query: str, department: str = "General", top_k: int = 3) -> str:
    """
    Retrieve the most relevant paragraphs from knowledge base documents
    for the given query and department.
    Returns a formatted context string.
    """
    # Extract keywords from the query (words > 3 chars)
    keywords = [w for w in re.findall(r"\b\w{4,}\b", query.lower()) if w not in
                {"what", "when", "where", "which", "that", "this", "have", "will",
                 "from", "with", "your", "they", "their", "there", "been", "were"}]

    doc_files = DEPT_DOCS.get(department, DEPT_DOCS["General"])
    scored = []

    for filename in doc_files:
        doc_text = _load_document(filename)
        if not doc_text:
            continue
        doc_name = DOCUMENTS.get(filename, filename)
        for para in _split_paragraphs(doc_text):
            score = _score_paragraph(para, keywords)
            if score > 0:
                scored.append((score, doc_name, para))

    if not scored:
        # Fallback: return first paragraph of each relevant doc
        fallback = []
        for filename in doc_files:
            doc_text = _load_document(filename)
            paras = _split_paragraphs(doc_text)
            if paras:
                fallback.append((DOCUMENTS.get(filename, filename), paras[0]))
        if fallback:
            return "\n\n".join(f"[{name}]\n{para}" for name, para in fallback[:top_k])
        return "No relevant information found in knowledge base."

    # Sort by score descending, take top_k
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]

    context_parts = [f"[{doc_name}]\n{para}" for _, doc_name, para in top]
    return "\n\n".join(context_parts)
