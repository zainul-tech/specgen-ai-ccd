"""
Database setup for SpecGen AI.

Uses SQLite for local development (zero setup). To switch to PostgreSQL/MySQL
for production (as specified in the SRS, Section 3.4), just change DATABASE_URL,
e.g. postgresql://user:pass@localhost/specgen — SQLAlchemy handles the rest.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./specgen.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
