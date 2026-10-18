"""Unit tests for the deterministic review engine (no DB, no network)."""
from app import review


def R(rid, text):
    return {"req_id": rid, "text": text}


def test_vague_term_without_number_is_ambiguous():
    res = review.review_requirements([R("REQ-1", "The system shall respond fast.")])[0]
    assert res["flag_type"] == "ambiguous"
    assert "fast" in res["flag_reason"]
    assert res["suggestion"]


def test_vague_term_with_measurable_criterion_is_not_flagged():
    res = review.review_requirements([R("REQ-1", "The system shall respond fast, within 2 seconds.")])[0]
    assert res["flag_type"] is None


def test_word_boundaries_prevent_false_positives():
    # "fastener" contains "fast"; "high-priority" contains "high" — neither is a vague use.
    for text in ["The system shall track fastener inventory.", "The system shall list high-priority items."]:
        assert review.review_requirements([R("REQ-1", text)])[0]["flag_type"] is None


def test_hyphenated_term_detected():
    assert review.find_vague_terms("The UI shall be user-friendly.") == ["user-friendly"]


def test_only_the_later_duplicate_is_flagged():
    reqs = [
        R("REQ-1", "The system shall allow customers to search restaurants by cuisine and location."),
        R("REQ-2", "Customers shall be able to search for restaurants by cuisine and location."),
    ]
    a, b = review.review_requirements(reqs)
    assert a["flag_type"] is None
    assert b["flag_type"] == "duplicate"
    assert "REQ-1" in b["flag_reason"]


def test_distinct_requirements_not_flagged_as_duplicates():
    reqs = [R("REQ-1", "The system shall let customers pay online by card."),
            R("REQ-2", "The system shall email an order confirmation to the customer.")]
    assert all(r["flag_type"] is None for r in review.review_requirements(reqs))


def test_duplicate_takes_priority_over_ambiguity():
    reqs = [R("REQ-1", "The system shall allow customers to search restaurants quickly."),
            R("REQ-2", "Customers shall be able to search restaurants quickly.")]
    assert review.review_requirements(reqs)[1]["flag_type"] == "duplicate"


def test_missing_areas_detected_and_covered_areas_excluded():
    reqs = [{"text": "Users shall log in with a password."}]
    missing = review.find_missing_areas(reqs)
    assert "Authentication / account access" not in missing
    assert "Data backup and recovery" in missing


def test_quality_score_bounds_and_behaviour():
    assert review.quality_score(0, 0, 0) == 0
    assert review.quality_score(10, 0, 0) == 100
    assert review.quality_score(10, 5, 0) == 50
    assert review.quality_score(10, 0, 3) == 88          # 100 - 12
    assert review.quality_score(10, 10, 8) == 0          # never negative
    assert review.quality_score(4, 0, 100) == 70         # missing-area penalty is capped at 30


# ---- threshold boundary tests: the pair above is an exact (1.0) match, so it can't pin the threshold ----

NEAR = ("The system shall allow customers to search restaurants by cuisine and location.",
        "Customers shall search restaurants by cuisine, location and price.")           # similarity ~0.83
BELOW = ("Customers shall search restaurants by cuisine.",
         "Customers shall search restaurants by cuisine, price, rating and distance.")  # similarity ~0.57


def test_similarity_values_are_what_the_boundary_tests_assume():
    assert 0.8 < review.jaccard(*NEAR) < 0.9
    assert 0.5 < review.jaccard(*BELOW) < review.DUPLICATE_THRESHOLD


def test_near_duplicate_above_threshold_is_flagged():
    a, b = review.review_requirements([R("REQ-1", NEAR[0]), R("REQ-2", NEAR[1])])
    assert b["flag_type"] == "duplicate"
    assert "83%" in b["flag_reason"]                 # reason reports the real similarity


def test_similar_but_below_threshold_is_not_flagged():
    a, b = review.review_requirements([R("REQ-1", BELOW[0]), R("REQ-2", BELOW[1])])
    assert b["flag_type"] is None


# ---- regression: keyword false negatives found while reviewing the UI output ----

def test_login_requirement_does_not_count_as_admin_or_monitoring_coverage():
    # "log in" once matched the keyword "log " and silently marked Administration as covered.
    missing = review.find_missing_areas([{"text": "Users shall log in with a password."}])
    assert "Administration / monitoring" in missing


def test_error_message_does_not_count_as_notification_coverage():
    missing = review.find_missing_areas([{"text": "The system shall show an error message on invalid input."}])
    assert "Notifications / user feedback" in missing


def test_genuine_coverage_is_still_recognised():
    covered = review.find_missing_areas([
        {"text": "The system shall write an audit log of every administrator action."},
        {"text": "The system shall send an email confirmation after each order."},
    ])
    assert "Administration / monitoring" not in covered
    assert "Notifications / user feedback" not in covered
