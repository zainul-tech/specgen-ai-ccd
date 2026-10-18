"""Sprint 4: cost estimate, sprint planning, risk editing, admin routes."""
from tests.conftest import IDEA


# ------------------------------------------------------------------ generation includes cost estimate

def test_generation_persists_cost_estimate(project):
    areas = {c["area"] for c in project["cost_estimates"]}
    assert areas == {"Frontend", "Backend", "AI integration & prompt tuning",
                      "Database", "Export/Reporting", "Testing"}


def test_generation_persists_risk_mitigation(project):
    assert project["risks"][0]["mitigation"]


# ------------------------------------------------------------------ risk editing

def test_edit_risk(client, project, auth_headers):
    risk_pk = project["risks"][0]["id"]
    r = client.patch(f"/projects/{project['id']}/risks/{risk_pk}",
                     json={"likelihood": "Low", "mitigation": "Use a secondary provider."},
                     headers=auth_headers)
    assert r.status_code == 200
    risk = r.json()["risks"][0]
    assert risk["likelihood"] == "Low"
    assert risk["mitigation"] == "Use a secondary provider."


def test_delete_risk(client, project, auth_headers):
    risk_pk = project["risks"][0]["id"]
    r = client.delete(f"/projects/{project['id']}/risks/{risk_pk}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["risks"] == []


def test_edit_risk_validation_rejects_bad_enum(client, project, auth_headers):
    risk_pk = project["risks"][0]["id"]
    r = client.patch(f"/projects/{project['id']}/risks/{risk_pk}",
                     json={"impact": "Catastrophic"}, headers=auth_headers)
    assert r.status_code == 422


def test_other_user_cannot_edit_or_delete_risk(client, project, other_headers):
    risk_pk = project["risks"][0]["id"]
    assert client.patch(f"/projects/{project['id']}/risks/{risk_pk}", json={"likelihood": "Low"},
                        headers=other_headers).status_code == 404
    assert client.delete(f"/projects/{project['id']}/risks/{risk_pk}", headers=other_headers).status_code == 404


# ------------------------------------------------------------------ cost estimate editing

def test_edit_cost_estimate(client, project, auth_headers):
    cost_pk = project["cost_estimates"][0]["id"]
    r = client.patch(f"/projects/{project['id']}/cost-estimate/{cost_pk}",
                     json={"effort_level": "Low", "notes": "Simpler than expected."}, headers=auth_headers)
    assert r.status_code == 200
    item = next(c for c in r.json()["cost_estimates"] if c["id"] == cost_pk)
    assert item["effort_level"] == "Low" and item["notes"] == "Simpler than expected."


# ------------------------------------------------------------------ sprint planning

def test_generate_sprint_plan_assigns_every_story(client, project, auth_headers):
    pid = project["id"]
    r = client.post(f"/projects/{pid}/sprint-plan", json={"sprint_count": 3, "duration_weeks": 1.5},
                    headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert len(body["sprints"]) == 3
    assert all(s["duration_weeks"] == 1.5 for s in body["sprints"])
    assigned_story_ids = {story["id"] for sprint in body["sprints"] for story in sprint["stories"]}
    assert assigned_story_ids == {s["id"] for s in body["user_stories"]}


def test_regenerating_sprint_plan_replaces_the_old_one(client, project, auth_headers):
    pid = project["id"]
    client.post(f"/projects/{pid}/sprint-plan", json={"sprint_count": 5, "duration_weeks": 1}, headers=auth_headers)
    r = client.post(f"/projects/{pid}/sprint-plan", json={"sprint_count": 2, "duration_weeks": 2}, headers=auth_headers)
    body = r.json()
    assert len(body["sprints"]) == 2  # old 5-sprint plan is gone, not merged


def test_sprint_plan_rejects_invalid_counts(client, project, auth_headers):
    pid = project["id"]
    assert client.post(f"/projects/{pid}/sprint-plan", json={"sprint_count": 0}, headers=auth_headers).status_code == 422
    assert client.post(f"/projects/{pid}/sprint-plan", json={"sprint_count": 50}, headers=auth_headers).status_code == 422


def test_sprint_plan_requires_user_stories(client, auth_headers, monkeypatch):
    from app import ai_engine
    monkeypatch.setattr(ai_engine, "generate_draft", lambda idea: {
        "classification": {}, "functionalRequirements": [], "userStories": [],
        "useCases": [], "risks": [], "testCases": [], "costEstimate": [],
    })
    pid = client.post("/projects", json={"idea_text": IDEA}, headers=auth_headers).json()["id"]
    r = client.post(f"/projects/{pid}/sprint-plan", json={"sprint_count": 2}, headers=auth_headers)
    assert r.status_code == 400


def test_move_story_to_another_sprint(client, project, auth_headers):
    pid = project["id"]
    client.post(f"/projects/{pid}/sprint-plan", json={"sprint_count": 3, "duration_weeks": 1}, headers=auth_headers)
    body = client.get(f"/projects/{pid}", headers=auth_headers).json()
    story_id = body["user_stories"][0]["id"]
    original_sprint = next(s["sprint_no"] for s in body["sprints"] if any(st["id"] == story_id for st in s["stories"]))
    target = 3 if original_sprint != 3 else 2

    r = client.patch(f"/projects/{pid}/stories/{story_id}/sprint", json={"sprint_no": target}, headers=auth_headers)
    assert r.status_code == 200
    updated = next(s for s in r.json()["sprints"] if s["sprint_no"] == target)
    assert any(st["id"] == story_id for st in updated["stories"])


def test_move_story_to_nonexistent_sprint_number_rejected(client, project, auth_headers):
    pid = project["id"]
    client.post(f"/projects/{pid}/sprint-plan", json={"sprint_count": 2, "duration_weeks": 1}, headers=auth_headers)
    story_id = client.get(f"/projects/{pid}", headers=auth_headers).json()["user_stories"][0]["id"]
    r = client.patch(f"/projects/{pid}/stories/{story_id}/sprint", json={"sprint_no": 99}, headers=auth_headers)
    assert r.status_code == 400


def test_other_user_cannot_generate_or_move_sprint_plan(client, project, other_headers):
    pid = project["id"]
    assert client.post(f"/projects/{pid}/sprint-plan", json={"sprint_count": 2}, headers=other_headers).status_code == 404
    assert client.patch(f"/projects/{pid}/stories/1/sprint", json={"sprint_no": 1},
                        headers=other_headers).status_code == 404


# ------------------------------------------------------------------ admin: access control

def test_admin_routes_require_auth(client):
    assert client.get("/admin/users").status_code == 401


def test_regular_user_forbidden_from_admin_routes(client, auth_headers):
    assert client.get("/admin/users", headers=auth_headers).status_code == 403
    assert client.get("/admin/usage", headers=auth_headers).status_code == 403
    assert client.patch("/admin/users/1/disable", headers=auth_headers).status_code == 403


# ------------------------------------------------------------------ admin: user management

def test_admin_lists_users_with_project_counts(client, project, auth_headers, admin_headers):
    r = client.get("/admin/users", headers=admin_headers)
    assert r.status_code == 200
    by_email = {u["email"]: u for u in r.json()}
    assert by_email["owner@test.edu"]["project_count"] == 1
    assert by_email["admin@test.edu"]["project_count"] == 0
    assert all(u["is_active"] for u in by_email.values())


def test_admin_can_disable_and_reenable_a_user(client, auth_headers, admin_headers):
    users = client.get("/admin/users", headers=admin_headers).json()
    owner_id = next(u["id"] for u in users if u["email"] == "owner@test.edu")

    r = client.patch(f"/admin/users/{owner_id}/disable", headers=admin_headers)
    assert r.status_code == 200 and r.json()["is_active"] is False

    r2 = client.patch(f"/admin/users/{owner_id}/enable", headers=admin_headers)
    assert r2.status_code == 200 and r2.json()["is_active"] is True


def test_disabled_users_existing_token_stops_working_immediately(client, auth_headers, admin_headers):
    """REQ-ADMIN-03: not just 'can't log in again' — an already-issued token must also stop working."""
    users = client.get("/admin/users", headers=admin_headers).json()
    owner_id = next(u["id"] for u in users if u["email"] == "owner@test.edu")

    assert client.get("/auth/me", headers=auth_headers).status_code == 200  # token is good before
    client.patch(f"/admin/users/{owner_id}/disable", headers=admin_headers)
    assert client.get("/auth/me", headers=auth_headers).status_code == 401  # same token, now rejected


def test_disabled_user_cannot_log_in_again(client, auth_headers, admin_headers):
    users = client.get("/admin/users", headers=admin_headers).json()
    owner_id = next(u["id"] for u in users if u["email"] == "owner@test.edu")
    client.patch(f"/admin/users/{owner_id}/disable", headers=admin_headers)

    r = client.post("/auth/login", json={"email": "owner@test.edu", "password": "password123"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Incorrect email or password."  # generic — doesn't reveal "disabled"


def test_admin_cannot_disable_their_own_account(client, admin_headers):
    me = client.get("/auth/me", headers=admin_headers).json()
    r = client.patch(f"/admin/users/{me['id']}/disable", headers=admin_headers)
    assert r.status_code == 400


def test_disable_nonexistent_user_404(client, admin_headers):
    assert client.patch("/admin/users/99999/disable", headers=admin_headers).status_code == 404


# ------------------------------------------------------------------ admin: usage stats (REQ-ADMIN-02/04)

def test_usage_stats_count_successful_and_failed_generations(client, auth_headers, admin_headers, mock_llm):
    client.post("/projects", json={"idea_text": IDEA}, headers=auth_headers)  # success, via mock_llm

    stats = client.get("/admin/usage", headers=admin_headers).json()
    assert stats["total_requests"] == 1
    assert stats["successful"] == 1
    assert stats["failed"] == 0
    assert stats["by_kind"]["generate_draft"] == 1


def test_usage_stats_count_failures_too(client, auth_headers, admin_headers, monkeypatch):
    from app import ai_engine
    def boom(idea):
        raise ai_engine.GenerationError("provider down")
    monkeypatch.setattr(ai_engine, "generate_draft", boom)
    client.post("/projects", json={"idea_text": IDEA}, headers=auth_headers)

    stats = client.get("/admin/usage", headers=admin_headers).json()
    assert stats["total_requests"] == 1
    assert stats["failed"] == 1
    assert stats["successful"] == 0
