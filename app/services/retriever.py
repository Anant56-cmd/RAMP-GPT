"""
In-Memory Semantic Cache and Golden Query Retrieval Service
Executes sub-millisecond similarity lookups over verified queries using hybrid
token-set Jaccard overlap and difflib SequenceMatcher without heavy neural vector DB overhead.
"""

import os
import json
import re
from difflib import SequenceMatcher
from typing import Optional, Tuple, List, Dict, Any
from app.config import GOLDEN_DATA_PATH

# In-memory cached golden queries
_GOLDEN_CACHE: List[Dict[str, str]] = []

def _normalize_text(text: str) -> str:
    """Lowercase, strip punctuation, and collapse whitespaces."""
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return " ".join(cleaned.split())

VEHICLE_ENTITIES = ["audi", "virtus", "thar", "scorpio", "innova", "land cruiser", "toyota", "volkswagen", "mahindra"]

def _has_entity_or_intent_mismatch(s1: str, s2: str) -> bool:
    """Checks if two queries have conflicting entities or incompatible intents."""
    # 1. Vehicle model/brand mismatch check
    v1 = {v for v in VEHICLE_ENTITIES if v in s1}
    v2 = {v for v in VEHICLE_ENTITIES if v in s2}
    if (v1 or v2) and v1 != v2:
        return True

    # 2. Customer name check (e.g. test customer 1 vs test customer 2 vs john doe)
    c1 = set(re.findall(r'(?:test\s*customer\s*\d+|customer\s*\d+|john\s*doe)', s1))
    c2 = set(re.findall(r'(?:test\s*customer\s*\d+|customer\s*\d+|john\s*doe)', s2))
    if (c1 or c2) and c1 != c2:
        return True

    # 3. Supervisor check (e.g. supervisor 1 vs supervisor x)
    sup1 = set(re.findall(r'supervisor\s*[a-z0-9]+', s1))
    sup2 = set(re.findall(r'supervisor\s*[a-z0-9]+', s2))
    if (sup1 or sup2) and sup1 != sup2:
        return True

    # 4. Aggregation intent mismatch check (Average vs Total / Parts vs Labour)
    toks1 = set(s1.split())
    toks2 = set(s2.split())
    avg_words = {"average", "avg", "mean"}
    total_words = {"total", "sum", "overall"}
    has_avg1 = bool(toks1 & avg_words)
    has_avg2 = bool(toks2 & avg_words)
    has_tot1 = bool(toks1 & total_words)
    has_tot2 = bool(toks2 & total_words)
    if has_avg1 and not has_avg2 and has_tot2:
        return True
    if has_avg2 and not has_avg1 and has_tot1:
        return True

    part_words = {"part", "parts", "spare", "spares"}
    labour_words = {"labour", "labor"}
    has_pr1 = bool(toks1 & part_words)
    has_pr2 = bool(toks2 & part_words)
    has_s1 = bool(toks1 & labour_words)
    has_s2 = bool(toks2 & labour_words)
    if has_pr1 and not has_pr2 and has_s2:
        return True
    if has_pr2 and not has_pr1 and has_s1:
        return True

    return False

def _compute_similarity(q1: str, q2: str, allow_few_shot: bool = False) -> float:
    """
    Computes a hybrid normalized similarity score (0.0 to 1.0)
    combining SequenceMatcher and token Jaccard similarity.
    Enforces strict entity and intent consistency for direct cache hits.
    """
    s1 = _normalize_text(q1)
    s2 = _normalize_text(q2)
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0

    # If queries refer to different entities or contradictory intents, direct caching is forbidden
    if not allow_few_shot and _has_entity_or_intent_mismatch(s1, s2):
        return 0.0

    ratio = SequenceMatcher(None, s1, s2).ratio()
    tok1 = set(s1.split())
    tok2 = set(s2.split())
    jaccard = len(tok1 & tok2) / max(len(tok1 | tok2), 1)

    return max(ratio, 0.7 * jaccard + 0.3 * ratio)

def load_golden_queries() -> List[Dict[str, str]]:
    """Loads golden queries from data/golden_queries.json into memory."""
    global _GOLDEN_CACHE
    if os.path.exists(GOLDEN_DATA_PATH):
        try:
            with open(GOLDEN_DATA_PATH, "r", encoding="utf-8") as f:
                _GOLDEN_CACHE = json.load(f)
        except Exception as e:
            print(f"> Warning: Failed to load golden queries: {e}")
            _GOLDEN_CACHE = []
    else:
        _GOLDEN_CACHE = []
    return _GOLDEN_CACHE

# Initialize on import
load_golden_queries()

def reload_golden_queries() -> List[Dict[str, str]]:
    """Force reloads the cache from disk."""
    return load_golden_queries()

def get_golden_match(user_query: str) -> Tuple[Optional[str], float, str]:
    """
    Returns (sql, distance_score, matched_query).
    Lower distance is better (0.0 = exact match).
    Distance <= 0.15 is considered a direct cache hit.
    """
    if not _GOLDEN_CACHE:
        load_golden_queries()

    best_match = None
    best_score = 0.0

    for item in _GOLDEN_CACHE:
        score = _compute_similarity(user_query, item.get("query", ""))
        if score > best_score:
            best_score = score
            best_match = item

    if best_match:
        distance = round(1.0 - best_score, 4)
        return best_match.get("sql"), distance, best_match.get("query", "")

    return None, 1.0, ""

def get_similar_example(user_query: str) -> Optional[str]:
    """
    Retrieves the most relevant Golden Query for few-shot prompt injection.
    Returns formatted prompt string if similarity >= 0.60 (distance <= 0.40).
    """
    if not _GOLDEN_CACHE:
        load_golden_queries()

    best_match = None
    best_score = 0.0

    for item in _GOLDEN_CACHE:
        score = _compute_similarity(user_query, item.get("query", ""), allow_few_shot=True)
        if score > best_score:
            best_score = score
            best_match = item

    if best_match and (1.0 - best_score) <= 0.40:
        return f"Query: {best_match.get('query')}\nSQL: {best_match.get('sql')}"
    return None

def save_golden_query(user_query: str, correct_sql: str) -> bool:
    """
    Appends or updates a verified query/SQL pair in:
    1. In-memory cache (_GOLDEN_CACHE)
    2. Local persistent storage (data/golden_queries.json)
    """
    global _GOLDEN_CACHE
    if not user_query or not correct_sql:
        return False

    q_clean = user_query.strip()
    sql_clean = correct_sql.strip()

    # Update in-memory cache
    norm_new = _normalize_text(q_clean)
    found = False
    for item in _GOLDEN_CACHE:
        if _normalize_text(item.get("query", "")) == norm_new:
            item["sql"] = sql_clean
            found = True
            break

    if not found:
        _GOLDEN_CACHE.append({
            "query": q_clean,
            "sql": sql_clean
        })

    return _persist_golden_queries()

def _persist_golden_queries() -> bool:
    """Writes the in-memory cache to data/golden_queries.json."""
    try:
        os.makedirs(os.path.dirname(GOLDEN_DATA_PATH), exist_ok=True)
        with open(GOLDEN_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(_GOLDEN_CACHE, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"> Error saving golden queries: {e}")
        return False
