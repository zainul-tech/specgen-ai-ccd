"""
Project routes.

Sprint 2: REQ-SUBMIT-01/02, REQ-AIGEN-01, REQ-STORY-01, REQ-RISK-01, REQ-TEST-01, REQ-SEC-03
Sprint 3: REQ-STORY-03 (use cases), REQ-AIGEN-03 (edit/add/delete requirements),
          REQ-REVIEW-01..06 (quality review)
Sprint 4: REQ-RISK-02 (cost estimate), REQ-SPRINT-01/02/03 (sprint planning),
          risk editing (consistency with "artifacts remain editable"), REQ-ADMIN-04 (generation log)
"""
import json
import re
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from .. import models, schemas, auth, ai_engine, review, planning, export
from ..database import get_db

router = APIRouter(prefix="/projects", tags=["projects"])


def get_owned_project(db: Session, project_id: int, user: models.User) -> models.Project:
    """REQ-SEC-03: one place that enforces ownership. A project you don't own is reported
    as 404 (not 403) so its existence isn't revealed."""
    project = (
        db.query(models.Project)
        .filter(models.Project.id == project_id, models.Project.owner_id == user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


def _invalidate_review(project: models.Project):
    """Any edit to the requirement set makes the last review's score/coverage stale."""
    project.quality_score = None
    project.missing_areas = None


def _log(db: Session, user_id: int, project_id, kind: str, success: bool, error: str = None):
    """REQ-ADMIN-04: log every AI generation attempt, success or failure."""
    db.add(models.GenerationLog(user_id=user_id, project_id=project_id, kind=kind,
                                 success=success, error=error))


# ---------------------------------------------------------------- create / read

@router.post("", response_model=schemas.ProjectOut, status_code=201)
def create_project(
    payload: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """REQ-SUBMIT-01/02 + REQ-AIGEN-01: submit the idea, classify it and generate the draft
    package in one call. (Splitting submit/generate into two UI steps is a later UX refinement.)"""
    project = models.Project(owner_id=current_user.id, idea_text=payload.idea_text)
    db.add(project)
    db.flush()  # need project.id for children and for the log row

    try:
        draft = ai_engine.generate_draft(payload.idea_text)
    except ai_engine.GenerationError as e:
        db.rollback()  # discard the flushed-but-uncommitted project — it never happened
        _log(db, current_user.id, None, "generate_draft", success=False, error=str(e))
        db.commit()  # log row is a fresh, separate insert in a new transaction
        raise HTTPException(status_code=502, detail=str(e))  # REQ-SUBMIT-04

    cls = draft.get("classification", {})
    project.classification_type = cls.get("type")
    project.classification_domain = cls.get("domain")
    project.classification_users = cls.get("users")

    priority_by_req_id = {}
    for r in draft.get("functionalRequirements", []):
        db.add(models.Requirement(project_id=project.id, req_id=r.get("id", "REQ-?"),
                                   text=r.get("text", ""), priority=r.get("priority", "Medium")))
        priority_by_req_id[r.get("id")] = r.get("priority", "Medium")

    # A story's priority follows the highest-priority requirement it's associated with;
    # since generation doesn't link them explicitly yet, default new stories to Medium
    # and let sprint planning (Sprint 4) treat unlinked stories as Medium too.
    for s in draft.get("userStories", []):
        db.add(models.UserStory(project_id=project.id, role=s.get("role", ""),
                                 goal=s.get("goal", ""), benefit=s.get("benefit", "")))
    for u in draft.get("useCases", []):
        db.add(models.UseCase(project_id=project.id, name=u.get("name", ""), actor=u.get("actor", ""),
                               precondition=u.get("precondition"), main_flow=u.get("mainFlow", ""),
                               postcondition=u.get("postcondition")))
    for r in draft.get("risks", []):
        db.add(models.Risk(project_id=project.id, description=r.get("description", ""),
                            likelihood=r.get("likelihood", "Medium"), impact=r.get("impact", "Medium"),
                            mitigation=r.get("mitigation")))
    for t in draft.get("testCases", []):
        db.add(models.TestCase(project_id=project.id, feature=t.get("feature", ""),
                                input_condition=t.get("input", ""), expected_result=t.get("expected", "")))
    for c in draft.get("costEstimate", []):
        db.add(models.CostEstimate(project_id=project.id, area=c.get("area", ""),
                                    effort_level=c.get("effortLevel", "Medium"), notes=c.get("notes")))

    _log(db, current_user.id, project.id, "generate_draft", success=True)
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=List[schemas.ProjectSummary])
def list_projects(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """REQ-SUBMIT-06, scoped to the owner (REQ-SEC-03)."""
    return (
        db.query(models.Project)
        .filter(models.Project.owner_id == current_user.id)
        .order_by(models.Project.created_at.desc())
        .all()
    )


@router.get("/{project_id}", response_model=schemas.ProjectOut)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    return get_owned_project(db, project_id, current_user)


@router.patch("/{project_id}/review", response_model=schemas.ProjectOut)
def mark_reviewed(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Business rule (SRS 5.3): Draft -> Reviewed."""
    project = get_owned_project(db, project_id, current_user)
    project.status = "Reviewed"
    db.commit()
    db.refresh(project)
    return project


# ---------------------------------------------------------------- requirement editing

def _next_req_id(project: models.Project) -> str:
    nums = [int(m.group(1)) for r in project.requirements
            if (m := re.fullmatch(r"REQ-(\d+)", r.req_id))]
    return f"REQ-{(max(nums) if nums else 0) + 1}"


@router.post("/{project_id}/requirements", response_model=schemas.ProjectOut, status_code=201)
def add_requirement(
    project_id: int,
    payload: schemas.RequirementCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """REQ-AIGEN-03: user adds their own requirement."""
    project = get_owned_project(db, project_id, current_user)
    db.add(models.Requirement(project_id=project.id, req_id=_next_req_id(project),
                               text=payload.text.strip(), priority=payload.priority))
    _invalidate_review(project)
    db.commit()
    db.refresh(project)
    return project


def _get_requirement(db: Session, project: models.Project, req_pk: int) -> models.Requirement:
    req = (db.query(models.Requirement)
           .filter(models.Requirement.id == req_pk, models.Requirement.project_id == project.id)
           .first())
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found.")
    return req


@router.patch("/{project_id}/requirements/{req_pk}", response_model=schemas.ProjectOut)
def update_requirement(
    project_id: int,
    req_pk: int,
    payload: schemas.RequirementUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """REQ-AIGEN-03 (edit text) and REQ-REVIEW-03 (override priority)."""
    project = get_owned_project(db, project_id, current_user)
    req = _get_requirement(db, project, req_pk)

    if payload.text is not None and payload.text.strip() != req.text:
        req.text = payload.text.strip()
        # The old flag described the old text — it no longer applies.
        req.flag_type = req.flag_reason = req.suggestion = req.suggestion_kind = None
    if payload.priority is not None:
        req.priority = payload.priority
    _invalidate_review(project)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}/requirements/{req_pk}", response_model=schemas.ProjectOut)
def delete_requirement(
    project_id: int,
    req_pk: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    project = get_owned_project(db, project_id, current_user)
    db.delete(_get_requirement(db, project, req_pk))
    _invalidate_review(project)
    db.commit()
    db.refresh(project)
    return project


# ---------------------------------------------------------------- quality review

@router.post("/{project_id}/quality-review", response_model=schemas.ProjectOut)
def run_quality_review(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """REQ-REVIEW-01/02/04/05/06. Flags are decided by deterministic rules (review.py);
    the LLM is only asked to improve the wording of suggestions and may be absent."""
    project = get_owned_project(db, project_id, current_user)
    reqs = sorted(project.requirements, key=lambda r: r.id)
    if not reqs:
        raise HTTPException(status_code=400, detail="Add at least one requirement before running a review.")

    results = review.review_requirements([{"req_id": r.req_id, "text": r.text} for r in reqs])
    by_id = {res["req_id"]: res for res in results}

    flagged_payload = [
        {"req_id": r.req_id, "text": r.text, "flag_reason": by_id[r.req_id]["flag_reason"]}
        for r in reqs if by_id[r.req_id]["flag_type"]
    ]
    try:
        improved = ai_engine.suggest_rewordings(flagged_payload)
        if flagged_payload:
            _log(db, current_user.id, project.id, "suggest_rewordings", success=True)
    except Exception as e:
        improved = {}
        _log(db, current_user.id, project.id, "suggest_rewordings", success=False, error=str(e))

    flagged_count = 0
    for r in reqs:
        res = by_id[r.req_id]
        r.flag_type, r.flag_reason = res["flag_type"], res["flag_reason"]
        if res["flag_type"] and improved.get(r.req_id):
            r.suggestion, r.suggestion_kind = improved[r.req_id], "rewrite"
        elif res["flag_type"]:
            r.suggestion, r.suggestion_kind = res["suggestion"], "advice"
        else:
            r.suggestion = r.suggestion_kind = None
        if res["flag_type"]:
            flagged_count += 1

    missing = review.find_missing_areas([{"text": r.text} for r in reqs])
    project.missing_areas = json.dumps(missing)
    project.quality_score = review.quality_score(len(reqs), flagged_count, len(missing))

    db.commit()
    db.refresh(project)
    return project


# ---------------------------------------------------------------- risks (Sprint 4)

def _get_risk(db: Session, project: models.Project, risk_pk: int) -> models.Risk:
    risk = (db.query(models.Risk)
            .filter(models.Risk.id == risk_pk, models.Risk.project_id == project.id).first())
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found.")
    return risk


@router.patch("/{project_id}/risks/{risk_pk}", response_model=schemas.ProjectOut)
def update_risk(
    project_id: int, risk_pk: int, payload: schemas.RiskUpdate,
    db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user),
):
    project = get_owned_project(db, project_id, current_user)
    risk = _get_risk(db, project, risk_pk)
    for field in ("description", "likelihood", "impact", "mitigation"):
        value = getattr(payload, field)
        if value is not None:
            setattr(risk, field, value.strip() if isinstance(value, str) else value)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}/risks/{risk_pk}", response_model=schemas.ProjectOut)
def delete_risk(
    project_id: int, risk_pk: int,
    db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user),
):
    project = get_owned_project(db, project_id, current_user)
    db.delete(_get_risk(db, project, risk_pk))
    db.commit()
    db.refresh(project)
    return project


# ---------------------------------------------------------------- cost estimate (Sprint 4)

@router.patch("/{project_id}/cost-estimate/{cost_pk}", response_model=schemas.ProjectOut)
def update_cost_estimate(
    project_id: int, cost_pk: int, payload: schemas.CostEstimateUpdate,
    db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user),
):
    project = get_owned_project(db, project_id, current_user)
    item = (db.query(models.CostEstimate)
            .filter(models.CostEstimate.id == cost_pk, models.CostEstimate.project_id == project.id).first())
    if not item:
        raise HTTPException(status_code=404, detail="Cost estimate item not found.")
    if payload.effort_level is not None:
        item.effort_level = payload.effort_level
    if payload.notes is not None:
        item.notes = payload.notes.strip()
    db.commit()
    db.refresh(project)
    return project


# ---------------------------------------------------------------- sprint planning (Sprint 4)

@router.post("/{project_id}/sprint-plan", response_model=schemas.ProjectOut)
def generate_sprint_plan(
    project_id: int, payload: schemas.SprintPlanRequest,
    db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user),
):
    """REQ-SPRINT-01/02. Re-running replaces the previous plan entirely — sprints and
    story assignments are regenerated from scratch, not merged with an old plan."""
    project = get_owned_project(db, project_id, current_user)
    stories = project.user_stories
    if not stories:
        raise HTTPException(status_code=400, detail="No user stories to plan yet.")

    for sprint in list(project.sprints):
        db.delete(sprint)
    db.flush()

    sprints = [models.Sprint(project_id=project.id, sprint_no=n, duration_weeks=payload.duration_weeks)
               for n in range(1, payload.sprint_count + 1)]
    db.add_all(sprints)
    db.flush()
    sprint_by_no = {s.sprint_no: s for s in sprints}

    story_ids = [s.id for s in stories]
    priorities = {s.id: (s.priority or "Medium") for s in stories}
    assignment = planning.assign_stories_to_sprints(story_ids, priorities, payload.sprint_count)
    for story in stories:
        story.sprint_id = sprint_by_no[assignment[story.id]].id

    db.commit()
    db.refresh(project)
    return project


@router.patch("/{project_id}/stories/{story_pk}/sprint", response_model=schemas.ProjectOut)
def move_story(
    project_id: int, story_pk: int, payload: schemas.StoryMoveRequest,
    db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user),
):
    """REQ-SPRINT-03: manually move a story to a different sprint."""
    project = get_owned_project(db, project_id, current_user)
    story = (db.query(models.UserStory)
             .filter(models.UserStory.id == story_pk, models.UserStory.project_id == project.id).first())
    if not story:
        raise HTTPException(status_code=404, detail="User story not found.")
    target = next((s for s in project.sprints if s.sprint_no == payload.sprint_no), None)
    if not target:
        raise HTTPException(status_code=400, detail=f"No sprint numbered {payload.sprint_no} in this plan.")
    story.sprint_id = target.id
    db.commit()
    db.refresh(project)
    return project


# ---------------------------------------------------------------- export (Sprint 5)

MEDIA_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@router.get("/{project_id}/export")
def export_project(
    project_id: int,
    format: str = "pdf",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """REQ-EXPORT-01 (PDF) / REQ-EXPORT-02 (DOCX). Both builders walk the same
    section order (export.py), so REQ-EXPORT-03 (structure preserved) holds for
    either format by construction, not by keeping two documents in sync by hand."""
    if format not in MEDIA_TYPES:
        raise HTTPException(status_code=400, detail="format must be 'pdf' or 'docx'.")
    project = get_owned_project(db, project_id, current_user)

    content = export.build_pdf(project) if format == "pdf" else export.build_docx(project)
    filename = f"specgen-ai-project-{project.id}.{format}"
    return Response(
        content=content,
        media_type=MEDIA_TYPES[format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
