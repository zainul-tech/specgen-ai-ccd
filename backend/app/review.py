"""
Requirement quality review — Sprint 3.

REQ-REVIEW-01  flag ambiguous requirements (vague term, no measurable criterion)
REQ-REVIEW-02  flag likely duplicates
REQ-REVIEW-04  suggest commonly expected but missing areas
REQ-REVIEW-06  single quality score per project

Deliberately rule-based and deterministic: the same input always gives the same
flags, it runs with no API key, and it is unit-testable. The LLM is only used
(optionally, in ai_engine.suggest_rewordings) to improve the *wording* of the
suggestions — never to decide what gets flagged.
"""
import re
from typing import List, Dict, Optional

# Vague terms that make a requirement unverifiable unless a measurable criterion is given.
VAGUE_TERMS = [
    "fast", "quick", "quickly", "user-friendly", "user friendly", "easy", "easily", "simple",
    "intuitive", "efficient", "efficiently", "robust", "flexible", "scalable", "secure",
    "reliable", "appropriate", "adequate", "reasonable", "good", "better", "best",
    "modern", "seamless", "smooth", "minimal", "large", "small", "high", "low",
]

# "Measurable" = the text contains a number (e.g. "2 seconds", "99%", "50 users").
_HAS_NUMBER = re.compile(r"\d")

STOPWORDS = {
    "the", "a", "an", "to", "of", "and", "or", "in", "on", "for", "with", "by", "be", "is",
    "are", "shall", "should", "must", "will", "can", "able", "allow", "system", "user", "users",
    "their", "his", "her", "its", "that", "this", "it", "as", "at", "from", "into", "so",
}

DUPLICATE_THRESHOLD = 0.6  # Jaccard similarity over content words

# Generic coverage checklist: area -> keywords that indicate it is already covered.
COVERAGE_CHECKLIST = {
    "Authentication / account access": ["login", "log in", "register", "sign up", "sign in", "password", "account"],
    "Error handling and validation": ["error", "invalid", "validation", "validate", "failure", "retry"],
    "Security and data protection": ["encrypt", "secure", "privacy", "authoriz", "permission", "hash", "protect"],
    "Notifications / user feedback": ["notif", "alert", "email", "sms", "confirmation"],
    "Search or filtering": ["search", "filter", "sort", "find"],
    "Administration / monitoring": ["admin", "monitor", "logging", "audit", "activity log"],
    "Data backup and recovery": ["backup", "recover", "restore"],
    "Performance targets": ["within", "seconds", "response time", "latency", "concurrent"],
}


def _tokens(text: str) -> set:
    words = re.findall(r"[a-z0-9\-]+", text.lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 2}


def jaccard(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def find_vague_terms(text: str) -> List[str]:
    lowered = text.lower()
    found = []
    for term in VAGUE_TERMS:
        if re.search(r"(?<![a-z\-])" + re.escape(term) + r"(?![a-z\-])", lowered):
            found.append(term)
    return found


def default_suggestion(term: str) -> str:
    return (f"Replace \"{term}\" with a measurable criterion "
            f"(e.g. a number and unit such as \"within 2 seconds\" or \"for 50 concurrent users\").")


def review_requirements(reqs: List[Dict]) -> List[Dict]:
    """
    reqs: [{"req_id": str, "text": str}, ...] in order.
    Returns one result per requirement:
      {"req_id", "flag_type": "ambiguous"|"duplicate"|None, "flag_reason", "suggestion"}
    A duplicate flag takes priority over an ambiguity flag (it is the more actionable issue).
    """
    results = []
    for i, r in enumerate(reqs):
        result = {"req_id": r["req_id"], "flag_type": None, "flag_reason": None, "suggestion": None}

        # Duplicate check against EARLIER requirements only, so exactly one of a pair is flagged.
        for j in range(i):
            score = jaccard(r["text"], reqs[j]["text"])
            if score >= DUPLICATE_THRESHOLD:
                result.update(
                    flag_type="duplicate",
                    flag_reason=f"Overlaps {int(score * 100)}% with {reqs[j]['req_id']}.",
                    suggestion=f"Merge with {reqs[j]['req_id']} or delete this requirement.",
                )
                break

        if result["flag_type"] is None:
            vague = find_vague_terms(r["text"])
            if vague and not _HAS_NUMBER.search(r["text"]):
                result.update(
                    flag_type="ambiguous",
                    flag_reason=f"Uses vague term \"{vague[0]}\" with no measurable criterion.",
                    suggestion=default_suggestion(vague[0]),
                )
        results.append(result)
    return results


def find_missing_areas(reqs: List[Dict]) -> List[str]:
    corpus = " ".join(r["text"].lower() for r in reqs)
    missing = []
    for area, keywords in COVERAGE_CHECKLIST.items():
        if not any(k in corpus for k in keywords):
            missing.append(area)
    return missing


def quality_score(total: int, flagged: int, missing: int) -> int:
    """0-100. Start from the share of clean requirements, then deduct 4 points per missing
    area (capped so coverage gaps alone can't zero the score)."""
    if total == 0:
        return 0
    base = 100 * (total - flagged) / total
    score = base - min(missing * 4, 30)
    return max(0, min(100, round(score)))
