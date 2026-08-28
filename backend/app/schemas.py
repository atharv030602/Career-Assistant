from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class StartRequest(BaseModel):
    resume_text: str = Field(..., min_length=30)
    target_roles: list[str] = Field(default_factory=list, max_length=5)


class ResumeStepRequest(BaseModel):
    # free-form feedback for the current HITL step; shape depends on waiting_for:
    #   learning_roadmap -> {"weekly_hours": int, "priority_skills": [str], "drop_skills": [str]}
    #   interview        -> {"focus_topics": [str]}
    feedback: dict[str, Any] = Field(default_factory=dict)


class SessionState(BaseModel):
    thread_id: str
    status: str  # running | interrupted | done
    waiting_for: str | None = None
    feedback_key: str | None = None
    fit_score: int = 0
    ai_powered: bool = False
    resume_review: dict[str, Any] | None = None
    skill_gaps: list[dict[str, Any]] = Field(default_factory=list)
    job_matches: list[dict[str, Any]] = Field(default_factory=list)
    roadmap: dict[str, Any] | None = None
    interview_kit: dict[str, Any] | None = None
    trace: list[str] = Field(default_factory=list)

    @classmethod
    def from_snapshot(cls, snap: dict) -> SessionState:
        s = snap["state"]
        return cls(
            thread_id=snap["thread_id"],
            status=snap["status"],
            waiting_for=snap["waiting_for"],
            feedback_key=snap["feedback_key"],
            fit_score=s.get("fit_score", 0),
            ai_powered=s.get("ai_powered", False),
            resume_review=s.get("resume_review"),
            skill_gaps=s.get("skill_gaps", []),
            job_matches=s.get("job_matches", []),
            roadmap=s.get("roadmap"),
            interview_kit=s.get("interview_kit"),
            trace=s.get("trace", []),
        )


class ReportResponse(BaseModel):
    thread_id: str
    status: str
    report_markdown: str


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    environment: str
    ai_enabled: bool
    llm_provider: str
    checkpoint_backend: str
