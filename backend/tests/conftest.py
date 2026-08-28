"""Force deterministic, in-memory mode before importing the app."""

import os

os.environ.setdefault("CHECKPOINT_BACKEND", "memory")
os.environ.setdefault("LLM_PROVIDER", "openai")
os.environ.setdefault("OPENAI_API_KEY", "")
os.environ.setdefault("GOOGLE_API_KEY", "")
os.environ.setdefault("LANGSMITH_TRACING", "false")

import pytest
from fastapi.testclient import TestClient

from app.main import app

RESUME = """
Atharv Mitkari — atharv@example.com — +91 90000 00000

Summary
Backend engineer, 3 years. Python and FastAPI services in production.

Experience
- Responsible for building REST APIs with FastAPI and PostgreSQL.
- Worked on migrating a monolith to Docker containers.
- Built a CI/CD pipeline with GitHub Actions for 12 services, cut deploy time 60%.
- Helped with on-call and incident response.

Skills
Python, FastAPI, Docker, PostgreSQL, REST APIs, Git, Linux, CI/CD, GitHub Actions

Education
B.E. Computer Science
"""


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture
def resume():
    return RESUME
