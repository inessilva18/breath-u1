# retriever.py
import json
from typing import List, Dict

RESOURCES_FILE = "resources.json"

def load_resources():
    try:
        with open(RESOURCES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def retrieve(query: str, k: int = 3) -> List[Dict[str, str]]:
    """
    Simple keyword-based retriever from local resources.
    """
    resources = load_resources()
    query_lower = query.lower()
    results = []
    for resource in resources:
        title = resource.get("title", "").lower()
        snippet = resource.get("snippet", "").lower()
        if query_lower in title or query_lower in snippet:
            results.append(resource)
    return results[:k]