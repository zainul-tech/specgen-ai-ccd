"""Unit tests for the deterministic sprint-assignment algorithm (no DB, no network)."""
import pytest
from app import planning
from app.planning import PRIORITY_ORDER


def test_high_priority_lands_in_earlier_sprints_than_low():
    ids = [1, 2, 3, 4]
    pri = {1: "Low", 2: "High", 3: "Low", 4: "High"}
    result = planning.assign_stories_to_sprints(ids, pri, sprint_count=2)
    # Both High-priority stories must be scheduled no later than any Low-priority story.
    high_sprints = [result[i] for i in (2, 4)]
    low_sprints = [result[i] for i in (1, 3)]
    assert max(high_sprints) <= min(low_sprints)


def test_every_story_assigned_exactly_once_to_a_valid_sprint():
    ids = list(range(1, 11))
    pri = {i: "Medium" for i in ids}
    result = planning.assign_stories_to_sprints(ids, pri, sprint_count=3)
    assert set(result.keys()) == set(ids)
    assert all(1 <= v <= 3 for v in result.values())


def test_equal_priority_stories_split_into_balanced_chunks():
    # 9 same-priority stories over 3 sprints should still split 3/3/3, not all into sprint 1 —
    # chunking by priority shouldn't mean chunking into one giant first sprint.
    ids = list(range(1, 10))
    pri = {i: "High" for i in ids}
    result = planning.assign_stories_to_sprints(ids, pri, sprint_count=3)
    counts = {n: list(result.values()).count(n) for n in (1, 2, 3)}
    assert counts == {1: 3, 2: 3, 3: 3}


def test_uneven_split_remainder_goes_to_earliest_sprints():
    # 10 stories over 3 sprints -> sizes must be 4/3/3 (remainder to the front), not 3/3/4.
    ids = list(range(1, 11))
    pri = {i: "Medium" for i in ids}
    result = planning.assign_stories_to_sprints(ids, pri, sprint_count=3)
    counts = [list(result.values()).count(n) for n in (1, 2, 3)]
    assert counts == [4, 3, 3]


def test_earlier_sprints_are_never_lower_priority_on_average():
    # Mixed priorities, uneven counts: every story in sprint N must be at least as high
    # priority as every story in sprint N+1 (contiguous chunking, not interleaved).
    ids = list(range(1, 8))
    pri = {1: "High", 2: "High", 3: "Medium", 4: "Medium", 5: "Medium", 6: "Low", 7: "Low"}
    result = planning.assign_stories_to_sprints(ids, pri, sprint_count=3)
    for sid, sprint_no in result.items():
        for other_id, other_sprint in result.items():
            if sprint_no < other_sprint:
                assert PRIORITY_ORDER[pri[sid]] <= PRIORITY_ORDER[pri[other_id]]


def test_story_with_no_linked_priority_defaults_to_medium_not_crash():
    ids = [1, 2]
    result = planning.assign_stories_to_sprints(ids, priorities={}, sprint_count=2)
    assert set(result.keys()) == {1, 2}


def test_single_sprint_gets_everything():
    ids = [1, 2, 3]
    pri = {1: "Low", 2: "High", 3: "Medium"}
    result = planning.assign_stories_to_sprints(ids, pri, sprint_count=1)
    assert all(v == 1 for v in result.values())


def test_zero_sprints_rejected():
    with pytest.raises(ValueError):
        planning.assign_stories_to_sprints([1], {1: "High"}, sprint_count=0)


def test_more_sprints_than_stories_leaves_some_sprints_empty_not_crash():
    result = planning.assign_stories_to_sprints([1, 2], {1: "High", 2: "Low"}, sprint_count=5)
    assert len(result) == 2
    assert all(1 <= v <= 5 for v in result.values())
