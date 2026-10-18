"""Test setup. Only the LLM call is mocked; routes, auth, ownership, the database and the
review engine all run for real against a throwaway SQLite file."""
import os

os.environ["DATABASE_URL"] = "sqlite:///./test_specgen.db"
os.environ["SECRET_KEY"] = "test-secret"
os.environ.pop("ANTHROPIC_API_KEY", None)  # tests must never depend on a real key

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, engine
from app import ai_engine

IDEA = "Develop an online food ordering app for restaurants with live tracking and payment."

CANNED_DRAFT = {
    "classification": {"type": "E-commerce marketplace", "domain": "Food service", "users": "Customers, restaurants"},
    "functionalRequirements": [
        {"id": "REQ-1", "text": "The system shall load restaurant pages fast.", "priority": "High"},
        {"id": "REQ-2", "text": "The system shall allow customers to search restaurants by cuisine and location.", "priority": "High"},
        {"id": "REQ-3", "text": "Customers shall be able to search for restaurants by cuisine and location.", "priority": "Medium"},
        {"id": "REQ-4", "text": "The system shall let customers pay online by card.", "priority": "High"},
    ],
    "userStories": [{"role": "customer", "goal": "to search restaurants", "benefit": "I can order food easily"}],
    "useCases": [{"name": "Place Order", "actor": "Customer", "precondition": "Customer is logged in",
                  "mainFlow": "1. Add items 2. Checkout 3. Pay", "postcondition": "Order is confirmed"}],
    "risks": [{"description": "Payment gateway failure", "likelihood": "Medium", "impact": "High",
               "mitigation": "Integrate a fallback payment provider and add retry logic."}],
    "testCases": [{"feature": "Checkout", "input": "Valid card", "expected": "Order confirmed"}],
    "costEstimate": [
        {"area": "Frontend", "effortLevel": "Medium", "notes": "Order flow + tracking UI"},
        {"area": "Backend", "effortLevel": "High", "notes": "API + order state machine"},
        {"area": "AI integration & prompt tuning", "effortLevel": "High", "notes": "Generation + review"},
        {"area": "Database", "effortLevel": "Low", "notes": "Standard relational schema"},
        {"area": "Export/Reporting", "effortLevel": "Low", "notes": "PDF/DOCX export"},
        {"area": "Testing", "effortLevel": "Medium", "notes": "Spread across sprints"},
    ],
}


@pytest.fixture
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


def _signup(client, email):
    client.post("/auth/register", json={"email": email, "password": "password123"})
    token = client.post("/auth/login", json={"email": email, "password": "password123"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers(client):
    return _signup(client, "owner@test.edu")


@pytest.fixture
def other_headers(client):
    return _signup(client, "intruder@test.edu")


@pytest.fixture
def admin_headers(client):
    """Signs up a user, then promotes them to admin directly via the DB —
    mirrors scripts/make_admin.py, which is the only real way to create one."""
    headers = _signup(client, "admin@test.edu")
    from app.database import SessionLocal
    from app import models
    db = SessionLocal()
    user = db.query(models.User).filter(models.User.email == "admin@test.edu").first()
    user.role = "admin"
    db.commit()
    db.close()
    return headers


@pytest.fixture
def mock_llm(monkeypatch):
    monkeypatch.setattr(ai_engine, "generate_draft", lambda idea: CANNED_DRAFT)


@pytest.fixture
def project(client, auth_headers, mock_llm):
    r = client.post("/projects", json={"idea_text": IDEA}, headers=auth_headers)
    assert r.status_code == 201, r.text
    return r.json()
