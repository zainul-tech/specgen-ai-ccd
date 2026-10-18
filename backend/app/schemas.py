"""Pydantic schemas — request/response shapes. Kept separate from ORM models
per good FastAPI practice, so the API contract can evolve independently of the DB schema."""
import json
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Literal
import datetime


# ---------- Auth ----------
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    role: str
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Project / generation ----------
class ProjectCreate(BaseModel):
    idea_text: str = Field(min_length=15, max_length=2000)


class RequirementOut(BaseModel):
    id: int
    req_id: str
    text: str
    priority: str
    flag_type: Optional[str] = None
    flag_reason: Optional[str] = None
    suggestion: Optional[str] = None
    suggestion_kind: Optional[str] = None
    class Config:
        from_attributes = True


class RequirementCreate(BaseModel):
    text: str = Field(min_length=5, max_length=1000)
    priority: Literal["High", "Medium", "Low"] = "Medium"


class RequirementUpdate(BaseModel):
    # Both optional: PATCH semantics — only provided fields change (REQ-AIGEN-03, REQ-REVIEW-03).
    text: Optional[str] = Field(default=None, min_length=5, max_length=1000)
    priority: Optional[Literal["High", "Medium", "Low"]] = None


class UseCaseOut(BaseModel):
    name: str
    actor: str
    precondition: Optional[str] = None
    main_flow: str
    postcondition: Optional[str] = None
    class Config:
        from_attributes = True


class UserStoryOut(BaseModel):
    id: int
    role: str
    goal: str
    benefit: str
    priority: str
    sprint_id: Optional[int] = None
    class Config:
        from_attributes = True


class RiskOut(BaseModel):
    id: int
    description: str
    likelihood: str
    impact: str
    mitigation: Optional[str] = None
    class Config:
        from_attributes = True


class RiskUpdate(BaseModel):
    description: Optional[str] = Field(default=None, min_length=5, max_length=500)
    likelihood: Optional[Literal["Low", "Medium", "High"]] = None
    impact: Optional[Literal["Low", "Medium", "High"]] = None
    mitigation: Optional[str] = Field(default=None, max_length=500)


class CostEstimateOut(BaseModel):
    id: int
    area: str
    effort_level: str
    notes: Optional[str] = None
    class Config:
        from_attributes = True


class CostEstimateUpdate(BaseModel):
    effort_level: Optional[Literal["Low", "Medium", "High"]] = None
    notes: Optional[str] = Field(default=None, max_length=500)


class SprintOut(BaseModel):
    id: int
    sprint_no: int
    duration_weeks: float
    stories: List[UserStoryOut] = []
    class Config:
        from_attributes = True


class SprintPlanRequest(BaseModel):
    sprint_count: int = Field(ge=1, le=12)
    duration_weeks: float = Field(default=1.0, ge=0.5, le=6)


class StoryMoveRequest(BaseModel):
    sprint_no: int = Field(ge=1)


class TestCaseOut(BaseModel):
    feature: str
    input_condition: str
    expected_result: str
    class Config:
        from_attributes = True


class ProjectOut(BaseModel):
    id: int
    idea_text: str
    classification_type: Optional[str]
    classification_domain: Optional[str]
    classification_users: Optional[str]
    status: str
    quality_score: Optional[int] = None
    missing_areas: List[str] = []
    created_at: datetime.datetime
    requirements: List[RequirementOut] = []
    user_stories: List[UserStoryOut] = []
    use_cases: List[UseCaseOut] = []
    risks: List[RiskOut] = []
    test_cases: List[TestCaseOut] = []
    cost_estimates: List[CostEstimateOut] = []
    sprints: List[SprintOut] = []

    @field_validator("missing_areas", mode="before")
    @classmethod
    def _parse_missing_areas(cls, v):
        # Stored as a JSON string in the DB; exposed as a list.
        if v is None or v == "":
            return []
        if isinstance(v, str):
            return json.loads(v)
        return v

    class Config:
        from_attributes = True


class ProjectSummary(BaseModel):
    id: int
    idea_text: str
    status: str
    created_at: datetime.datetime
    class Config:
        from_attributes = True


# ---------- Admin (REQ-ADMIN-01/02/03) ----------
class UserAdminOut(BaseModel):
    id: int
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime.datetime
    project_count: int
    class Config:
        from_attributes = True


class UsageStats(BaseModel):
    total_requests: int
    successful: int
    failed: int
    by_kind: dict
