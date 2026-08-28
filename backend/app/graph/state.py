"""Shared graph state + the typed slice each agent writes."""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from pydantic import BaseModel, Field

# --------------------------------------------------------------------------
# Typed slices
# --------------------------------------------------------------------------


class ResumeReview(BaseModel):
    strengths: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    rewritten_bullets: list[str] = Field(default_factory=list)
    readability_note: str = ""


class SkillGap(BaseModel):
    skill: str
    importance: str = "medium"  # high | medium | low
    present_in_resume: bool = False
    recommendation: str = ""


class JobMatch(BaseModel):
    role: str
    match_score: int = 0
    rationale: str = ""
    key_missing: list[str] = Field(default_factory=list)


class RoadmapPhase(BaseModel):
    name: str
    weeks: int
    focus_skills: list[str] = Field(default_factory=list)
    resources: list[str] = Field(default_factory=list)
    milestone: str = ""


class Roadmap(BaseModel):
    total_weeks: int = 0
    weekly_hours: int = 6
    phases: list[RoadmapPhase] = Field(default_factory=list)


class InterviewQuestion(BaseModel):
    topic: str
    question: str
    kind: str = "technical"  # technical | behavioural | system-design


class InterviewKit(BaseModel):
    questions: list[InterviewQuestion] = Field(default_factory=list)
    star_answers: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Graph state
# --------------------------------------------------------------------------


class CareerState(TypedDict, total=False):
    thread_id: str
    # inputs
    resume_text: str
    target_roles: list[str]
    # agent outputs
    resume_review: dict[str, Any] | None
    skill_gaps: list[dict[str, Any]]
    fit_score: int
    job_matches: list[dict[str, Any]]
    roadmap: dict[str, Any] | None
    interview_kit: dict[str, Any] | None
    final_report: str
    # control
    revisions: int
    human_feedback: dict[str, Any]
    trace: Annotated[list[str], operator.add]
    ai_powered: bool


def initial_state(thread_id: str, resume_text: str, target_roles: list[str]) -> CareerState:
    return CareerState(
        thread_id=thread_id,
        resume_text=resume_text,
        target_roles=target_roles,
        resume_review=None,
        skill_gaps=[],
        fit_score=0,
        job_matches=[],
        roadmap=None,
        interview_kit=None,
        final_report="",
        revisions=0,
        human_feedback={},
        trace=[],
        ai_powered=False,
    )
