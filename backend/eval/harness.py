"""Drive one graph run to completion with synthetic human feedback."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.graph.build import get_graph
from app.graph.state import initial_state

# Default feedback injected at the two HITL checkpoints during eval.
_DEFAULT_FEEDBACK = {
    "skill_gap": {"weekly_hours": 6, "drop_skills": [], "priority_skills": []},
    "roadmap": {"focus_topics": []},
}


@dataclass
class RunResult:
    case_id: str
    ok: bool
    error: str | None
    latency_ms: float
    state: dict[str, Any] = field(default_factory=dict)
    pending: list[str] = field(default_factory=list)


def run_case(resume_text: str, target_roles: list[str], case_id: str = "") -> RunResult:
    graph = get_graph()
    tid = uuid.uuid4().hex
    cfg = {"configurable": {"thread_id": tid}}
    started = time.perf_counter()
    error = None
    try:
        graph.invoke(initial_state(tid, resume_text, target_roles), cfg)
        # Inject both feedback slices up front; each HITL node reads its own key.
        graph.update_state(cfg, {"human_feedback": dict(_DEFAULT_FEEDBACK)})
        graph.invoke(None, cfg)  # past HITL #1 (learning_roadmap)
        graph.invoke(None, cfg)  # past HITL #2 (interview)
    except Exception as exc:  # noqa: BLE001 - eval must record, not raise
        error = repr(exc)

    snap = graph.get_state(cfg)
    return RunResult(
        case_id=case_id,
        ok=error is None and bool(snap.values.get("final_report")) and not snap.next,
        error=error,
        latency_ms=round((time.perf_counter() - started) * 1000, 1),
        state=snap.values,
        pending=list(snap.next),
    )
