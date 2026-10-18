"""API-level tests: real routes, auth, ownership and DB; only the LLM call is mocked."""
from app import ai_engine
from tests.conftest import IDEA


# ------------------------------------------------------------------ Sprint 1 / 2 basics

def test_protected_routes_require_auth(client):
    assert client.get("/projects").status_code == 401
    assert client.post("/projects", json={"idea_text": IDEA}).status_code == 401


def test_generation_persists_everything_including_use_cases(project):
    assert project["classification_domain"] == "Food service"
    assert len(project["requirements"]) == 4
    assert len(project["user_stories"]) == 1
    assert project["use_cases"][0]["name"] == "Place Order"
    assert project["use_cases"][0]["postcondition"] == "Order is confirmed"
    assert project["quality_score"] is None and project["missing_areas"] == []


def test_short_idea_rejected(client, auth_headers, mock_llm):
    r = client.post("/projects", json={"idea_text": "too short"}, headers=auth_headers)
    assert r.status_code == 422


def test_generation_failure_returns_502_and_persists_nothing(client, auth_headers, monkeypatch):
    def boom(idea):
        raise ai_engine.GenerationError("provider down")
    monkeypatch.setattr(ai_engine, "generate_draft", boom)
    r = client.post("/projects", json={"idea_text": IDEA}, headers=auth_headers)
    assert r.status_code == 502
    assert "provider down" in r.json()["detail"]
    assert client.get("/projects", headers=auth_headers).json() == []


# ------------------------------------------------------------------ ownership (REQ-SEC-03)

def test_other_user_cannot_see_or_modify_project(client, project, other_headers):
    pid = project["id"]
    req_pk = project["requirements"][0]["id"]
    assert client.get(f"/projects/{pid}", headers=other_headers).status_code == 404
    assert client.post(f"/projects/{pid}/quality-review", headers=other_headers).status_code == 404
    assert client.patch(f"/projects/{pid}/requirements/{req_pk}", json={"priority": "Low"},
                        headers=other_headers).status_code == 404
    assert client.delete(f"/projects/{pid}/requirements/{req_pk}", headers=other_headers).status_code == 404
    assert client.post(f"/projects/{pid}/requirements", json={"text": "Sneaky requirement"},
                       headers=other_headers).status_code == 404
    assert client.get("/projects", headers=other_headers).json() == []


# ------------------------------------------------------------------ Sprint 3: quality review

def test_quality_review_flags_ambiguity_and_duplicates(client, project, auth_headers):
    r = client.post(f"/projects/{project['id']}/quality-review", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    flags = {q["req_id"]: q for q in body["requirements"]}

    assert flags["REQ-1"]["flag_type"] == "ambiguous"        # "fast", no number
    assert flags["REQ-1"]["suggestion"]
    assert flags["REQ-2"]["flag_type"] is None
    assert flags["REQ-3"]["flag_type"] == "duplicate"        # near-copy of REQ-2
    assert "REQ-2" in flags["REQ-3"]["flag_reason"]
    assert flags["REQ-4"]["flag_type"] is None

    assert isinstance(body["quality_score"], int) and 0 <= body["quality_score"] <= 100
    assert body["quality_score"] < 100                        # 2 of 4 flagged
    assert "Authentication / account access" in body["missing_areas"]  # no login requirement in draft


def test_review_uses_llm_rewording_when_available(client, project, auth_headers, monkeypatch):
    monkeypatch.setattr(ai_engine, "suggest_rewordings",
                        lambda flagged: {"REQ-1": "The system shall load restaurant pages within 2 seconds."})
    body = client.post(f"/projects/{project['id']}/quality-review", headers=auth_headers).json()
    flags = {q["req_id"]: q for q in body["requirements"]}
    assert flags["REQ-1"]["suggestion"] == "The system shall load restaurant pages within 2 seconds."
    assert flags["REQ-1"]["suggestion_kind"] == "rewrite"     # safe for the UI to apply as-is
    assert "Merge" in flags["REQ-3"]["suggestion"]            # no LLM rewording -> rule-based suggestion kept
    assert flags["REQ-3"]["suggestion_kind"] == "advice"      # instruction, must NOT be applied as requirement text
    assert flags["REQ-2"]["suggestion"] is None and flags["REQ-2"]["suggestion_kind"] is None


def test_review_without_llm_still_works(client, project, auth_headers):
    # conftest removes ANTHROPIC_API_KEY, so suggest_rewordings returns {} for real here.
    r = client.post(f"/projects/{project['id']}/quality-review", headers=auth_headers)
    assert r.status_code == 200
    flagged = [q for q in r.json()["requirements"] if q["flag_type"]]
    assert flagged and all(q["suggestion_kind"] == "advice" for q in flagged)


def test_review_requires_requirements(client, project, auth_headers):
    for r in project["requirements"]:
        client.delete(f"/projects/{project['id']}/requirements/{r['id']}", headers=auth_headers)
    r = client.post(f"/projects/{project['id']}/quality-review", headers=auth_headers)
    assert r.status_code == 400


# ------------------------------------------------------------------ Sprint 3: editing

def test_editing_text_clears_flag_and_invalidates_score(client, project, auth_headers):
    pid = project["id"]
    client.post(f"/projects/{pid}/quality-review", headers=auth_headers)
    req1 = next(r for r in client.get(f"/projects/{pid}", headers=auth_headers).json()["requirements"]
                if r["req_id"] == "REQ-1")
    assert req1["flag_type"] == "ambiguous"

    r = client.patch(f"/projects/{pid}/requirements/{req1['id']}",
                     json={"text": "The system shall load restaurant pages within 2 seconds."}, headers=auth_headers)
    body = r.json()
    edited = next(q for q in body["requirements"] if q["req_id"] == "REQ-1")
    assert edited["text"].endswith("within 2 seconds.")
    assert edited["flag_type"] is None                        # stale flag removed
    assert edited["suggestion"] is None and edited["suggestion_kind"] is None
    assert body["quality_score"] is None                      # must re-run the review


def test_priority_override_and_validation(client, project, auth_headers):
    pid, req_pk = project["id"], project["requirements"][0]["id"]
    ok = client.patch(f"/projects/{pid}/requirements/{req_pk}", json={"priority": "Low"}, headers=auth_headers)
    assert ok.status_code == 200
    assert next(q for q in ok.json()["requirements"] if q["id"] == req_pk)["priority"] == "Low"
    bad = client.patch(f"/projects/{pid}/requirements/{req_pk}", json={"priority": "Urgent"}, headers=auth_headers)
    assert bad.status_code == 422


def test_add_requirement_gets_next_id_and_delete_works(client, project, auth_headers):
    pid = project["id"]
    added = client.post(f"/projects/{pid}/requirements",
                        json={"text": "The system shall email order confirmations.", "priority": "High"},
                        headers=auth_headers)
    assert added.status_code == 201
    assert added.json()["requirements"][-1]["req_id"] == "REQ-5"

    new_pk = added.json()["requirements"][-1]["id"]
    after = client.delete(f"/projects/{pid}/requirements/{new_pk}", headers=auth_headers).json()
    assert len(after["requirements"]) == 4
    assert client.delete(f"/projects/{pid}/requirements/{new_pk}", headers=auth_headers).status_code == 404


def test_mark_reviewed(client, project, auth_headers):
    r = client.patch(f"/projects/{project['id']}/review", headers=auth_headers)
    assert r.json()["status"] == "Reviewed"
