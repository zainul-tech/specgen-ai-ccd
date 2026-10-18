"""
Sprint planning — REQ-SPRINT-01/02.

Deliberately deterministic, not an LLM call — same rationale as review.py.
Which sprint a story lands in should be reproducible and explainable ("it's
High priority, so it's early"), not something that changes if you regenerate.
"""
from typing import List, Dict

PRIORITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}


def assign_stories_to_sprints(story_ids: List[int], priorities: Dict[int, str], sprint_count: int) -> Dict[int, int]:
    """
    REQ-SPRINT-02: distribute stories across `sprint_count` sprints (1-indexed),
    prioritizing High-priority items into earlier sprints.

    story_ids: ordered list of UserStory primary keys (generation order = original intent order)
    priorities: story_id -> requirement priority the story implements ("High"/"Medium"/"Low"),
                defaults to "Medium" for a story with no clearly linked requirement
    Returns: story_id -> sprint_number (1..sprint_count)

    Approach: stable-sort stories by priority (ties keep original order), then cut that
    sorted list into `sprint_count` contiguous, size-balanced chunks — sprint 1 gets the
    first (highest-priority) chunk, sprint 2 the next, and so on. This is deliberately
    NOT round-robin dealing: round-robin spreads every priority level across every sprint
    evenly, which satisfies "balanced workload" but actively contradicts "High-priority
    items in earlier sprints" (REQ-SPRINT-02) — a High item could land in the last sprint
    just because of its position in the deal order. Contiguous chunking keeps both
    properties: earlier sprints are strictly higher-priority on average, and chunk sizes
    still differ by at most one story (remainder distributed to the earliest sprints).
    """
    if sprint_count < 1:
        raise ValueError("sprint_count must be at least 1")
    ordered = sorted(story_ids, key=lambda sid: PRIORITY_ORDER.get(priorities.get(sid, "Medium"), 1))

    n = len(ordered)
    base, remainder = divmod(n, sprint_count)
    assignment = {}
    idx = 0
    for sprint_no in range(1, sprint_count + 1):
        size = base + (1 if sprint_no <= remainder else 0)
        for _ in range(size):
            assignment[ordered[idx]] = sprint_no
            idx += 1
    return assignment
