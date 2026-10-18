"""
ORM models for Sprint 1 (auth), Sprint 2 (idea submission, generation) and
Sprint 3 (use cases, requirement quality review).

Matches the Data Model Overview in the SRS (Section 5.7). All nine entities from
that section now exist as of Sprint 4.
"""
import datetime
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Float
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user")  # "user" | "admin"
    is_active = Column(Boolean, default=True)  # REQ-ADMIN-03: disabled accounts can't log in
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    idea_text = Column(Text, nullable=False)
    classification_type = Column(String, nullable=True)
    classification_domain = Column(String, nullable=True)
    classification_users = Column(String, nullable=True)
    status = Column(String, default="Draft")  # "Draft" | "Reviewed" — REQ business rule
    quality_score = Column(Integer, nullable=True)   # REQ-REVIEW-06, null until a review is run
    missing_areas = Column(Text, nullable=True)      # REQ-REVIEW-04, JSON-encoded list of strings
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    owner = relationship("User", back_populates="projects")
    requirements = relationship("Requirement", back_populates="project", cascade="all, delete-orphan")
    user_stories = relationship("UserStory", back_populates="project", cascade="all, delete-orphan")
    use_cases = relationship("UseCase", back_populates="project", cascade="all, delete-orphan")
    risks = relationship("Risk", back_populates="project", cascade="all, delete-orphan")
    test_cases = relationship("TestCase", back_populates="project", cascade="all, delete-orphan")
    cost_estimates = relationship("CostEstimate", back_populates="project", cascade="all, delete-orphan")
    sprints = relationship("Sprint", back_populates="project", cascade="all, delete-orphan",
                            order_by="Sprint.sprint_no")


class Requirement(Base):
    __tablename__ = "requirements"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    req_id = Column(String, nullable=False)       # e.g. "REQ-1" — display identifier, not PK
    text = Column(Text, nullable=False)
    priority = Column(String, default="Medium")   # High | Medium | Low
    flag_type = Column(String, nullable=True)      # "ambiguous" | "duplicate" | None (REQ-REVIEW-01/02)
    flag_reason = Column(Text, nullable=True)
    suggestion = Column(Text, nullable=True)       # REQ-REVIEW-05
    suggestion_kind = Column(String, nullable=True)  # "rewrite" (drop-in replacement text) | "advice" (instruction)

    project = relationship("Project", back_populates="requirements")


class UserStory(Base):
    __tablename__ = "user_stories"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    role = Column(String, nullable=False)
    goal = Column(Text, nullable=False)
    benefit = Column(Text, nullable=False)
    priority = Column(String, default="Medium")     # copied from linked requirement at generation time
    sprint_id = Column(Integer, ForeignKey("sprints.id"), nullable=True)  # REQ-SPRINT-02/03

    project = relationship("Project", back_populates="user_stories")
    sprint = relationship("Sprint", back_populates="stories")


class UseCase(Base):
    __tablename__ = "use_cases"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String, nullable=False)
    actor = Column(String, nullable=False)
    precondition = Column(Text, nullable=True)
    main_flow = Column(Text, nullable=False)
    postcondition = Column(Text, nullable=True)

    project = relationship("Project", back_populates="use_cases")


class Risk(Base):
    __tablename__ = "risks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    description = Column(Text, nullable=False)
    likelihood = Column(String, default="Medium")
    impact = Column(String, default="Medium")
    mitigation = Column(Text, nullable=True)  # Section 6 of the SRS pairs every risk with a mitigation

    project = relationship("Project", back_populates="risks")


class CostEstimate(Base):
    __tablename__ = "cost_estimates"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    area = Column(String, nullable=False)             # e.g. "Backend (FastAPI/Flask)"
    effort_level = Column(String, default="Medium")    # Low | Medium | High — relative effort, not currency
    notes = Column(Text, nullable=True)

    project = relationship("Project", back_populates="cost_estimates")


class Sprint(Base):
    __tablename__ = "sprints"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    sprint_no = Column(Integer, nullable=False)        # 1-indexed
    duration_weeks = Column(Float, default=1.0)

    project = relationship("Project", back_populates="sprints")
    stories = relationship("UserStory", back_populates="sprint")


class GenerationLog(Base):
    """REQ-ADMIN-04: every AI generation request, for auditing/debugging."""
    __tablename__ = "generation_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)  # null if generation failed before a project existed
    kind = Column(String, nullable=False)   # "generate_draft" | "suggest_rewordings"
    success = Column(Boolean, default=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class TestCase(Base):
    __tablename__ = "test_cases"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    feature = Column(String, nullable=False)
    input_condition = Column(Text, nullable=False)
    expected_result = Column(Text, nullable=False)

    project = relationship("Project", back_populates="test_cases")
