"""Admin routes — REQ-ADMIN-01 (list users), REQ-ADMIN-02 (usage stats),
REQ-ADMIN-03 (disable account). All gated by auth.require_admin."""
from collections import Counter
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=List[schemas.UserAdminOut])
def list_users(
    db: Session = Depends(get_db),
    _admin: models.User = Depends(auth.require_admin),
):
    """REQ-ADMIN-01. project_count computed in one query rather than N+1 per user."""
    counts = dict(
        db.query(models.Project.owner_id, func.count(models.Project.id))
        .group_by(models.Project.owner_id).all()
    )
    users = db.query(models.User).order_by(models.User.created_at.desc()).all()
    return [
        schemas.UserAdminOut(
            id=u.id, email=u.email, role=u.role, is_active=u.is_active,
            created_at=u.created_at, project_count=counts.get(u.id, 0),
        )
        for u in users
    ]


@router.patch("/users/{user_id}/disable", response_model=schemas.UserAdminOut)
def disable_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(auth.require_admin),
):
    """REQ-ADMIN-03. Existing tokens for this user stop working immediately
    (enforced in auth.get_current_user, not just at their next login)."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot disable your own account.")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user.is_active = False
    db.commit()
    db.refresh(user)
    project_count = db.query(models.Project).filter(models.Project.owner_id == user.id).count()
    return schemas.UserAdminOut(id=user.id, email=user.email, role=user.role,
                                 is_active=user.is_active, created_at=user.created_at,
                                 project_count=project_count)


@router.patch("/users/{user_id}/enable", response_model=schemas.UserAdminOut)
def enable_user(
    user_id: int,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(auth.require_admin),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user.is_active = True
    db.commit()
    db.refresh(user)
    project_count = db.query(models.Project).filter(models.Project.owner_id == user.id).count()
    return schemas.UserAdminOut(id=user.id, email=user.email, role=user.role,
                                 is_active=user.is_active, created_at=user.created_at,
                                 project_count=project_count)


@router.get("/usage", response_model=schemas.UsageStats)
def usage_stats(
    db: Session = Depends(get_db),
    _admin: models.User = Depends(auth.require_admin),
):
    """REQ-ADMIN-02: aggregate view over the generation log (REQ-ADMIN-04 populates it)."""
    logs = db.query(models.GenerationLog).all()
    by_kind = Counter(l.kind for l in logs)
    return schemas.UsageStats(
        total_requests=len(logs),
        successful=sum(1 for l in logs if l.success),
        failed=sum(1 for l in logs if not l.success),
        by_kind=dict(by_kind),
    )
