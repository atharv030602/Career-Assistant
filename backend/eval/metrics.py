"""Metrics over a single graph RunResult.

Deterministic metrics need no network. The two LLM-as-judge metrics run only
when a provider key is configured; otherwise they return None.
"""

from __future__ import annotations

import json

from app.core.llm import ai_enabled, llm_json
from app.services.skills import SKILL_ALIASES

_ALIAS_TO_CANON = {a: canon for canon, aliases in SKILL_ALIASES.items() for a in aliases}
_ALIAS_TO_CANON.update({canon: canon for canon in SKILL_ALIASES})

# nodes we expect in every completed run's trace (job_match is conditional)
_CORE_NODES = (
    "intake",
    "resume_review_agent",
    "skill_gap_agent",
    "learning_roadmap_agent",
    "interview_agent",
    "synthesize",
)


def canon(name: str) -> str:
    return _ALIAS_TO_CANON.get(name.strip().lower(), name.strip().lower())


def _canon_set(names: list[str]) -> set[str]:
    return {canon(n) for n in names}


def skill_gap_recall(state: dict, expected_missing: list[str]) -> float | None:
    if not expected_missing:
        return None
    predicted = _canon_set([g["skill"] for g in state.get("skill_gaps", [])])
    expected = _canon_set(expected_missing)
    return round(len(predicted & expected) / len(expected), 3)


def skill_gap_precision_against_present(state: dict, expected_present: list[str]) -> float | None:
    """Of the skills the resume clearly HAS, how few were wrongly flagged missing.
    1.0 = no false positives against the known-present set."""
    if not expected_present:
        return None
    predicted = _canon_set([g["skill"] for g in state.get("skill_gaps", [])])
    present = _canon_set(expected_present)
    false_pos = predicted & present
    return round(1 - len(false_pos) / len(present), 3)


def routing_correct(state: dict, expect_job_match: bool) -> bool:
    ran_job_match = any("job_match_agent" in t for t in state.get("trace", []))
    return ran_job_match == expect_job_match


def node_coverage(state: dict) -> float:
    trace = " ".join(state.get("trace", []))
    hit = sum(1 for n in _CORE_NODES if n in trace)
    return round(hit / len(_CORE_NODES), 3)


def roadmap_covers_high_gaps(state: dict) -> float | None:
    gaps = [canon(g["skill"]) for g in state.get("skill_gaps", []) if g.get("importance") == "high"]
    if not gaps:
        return None
    rm = state.get("roadmap") or {}
    in_plan = {canon(s) for p in rm.get("phases", []) for s in p.get("focus_skills", [])}
    return round(len(set(gaps) & in_plan) / len(set(gaps)), 3)


def interview_covers_top_gaps(state: dict, k: int = 3) -> float | None:
    gaps = [canon(g["skill"]) for g in state.get("skill_gaps", [])][:k]
    if not gaps:
        return None
    kit = state.get("interview_kit") or {}
    blob = " ".join(
        f"{q.get('topic', '')} {q.get('question', '')}" for q in kit.get("questions", [])
    ).lower()
    hit = sum(1 for g in gaps if g in blob or g.replace(" ", "") in blob.replace(" ", ""))
    return round(hit / len(gaps), 3)


# --------------------------------------------------------------------------
# LLM-as-judge (optional)
# --------------------------------------------------------------------------

_JUDGE_SYS = (
    "You are a strict evaluator. Score 1-5 (5 = excellent). "
    'Return STRICT JSON: {"score": <int>, "reason": "<one sentence>"}.'
)


def _judge(user: str) -> dict | None:
    if not ai_enabled():
        return None
    data = llm_json(_JUDGE_SYS, user)
    if isinstance(data, dict) and isinstance(data.get("score"), int):
        return {"score": max(1, min(5, data["score"])), "reason": str(data.get("reason", ""))}
    return None


def judge_roadmap_relevance(state: dict) -> dict | None:
    gaps = [g["skill"] for g in state.get("skill_gaps", [])]
    rm = state.get("roadmap") or {}
    return _judge(
        f"Skill gaps: {gaps}\n\nProposed learning roadmap:\n{json.dumps(rm)[:2500]}\n\n"
        "Does the roadmap address the high-priority gaps in a sensible order with real resources?"
    )


def judge_interview_quality(state: dict) -> dict | None:
    gaps = [g["skill"] for g in state.get("skill_gaps", [])][:5]
    kit = state.get("interview_kit") or {}
    return _judge(
        f"Top skill gaps: {gaps}\n\nInterview kit:\n{json.dumps(kit)[:2500]}\n\n"
        "Do the questions meaningfully probe these gaps and mix technical + behavioural?"
    )
