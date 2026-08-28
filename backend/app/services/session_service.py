"""Drive the LangGraph state machine over a thread_id lifecycle."""

from __future__ import annotations

import uuid

from app.core.errors import ConflictError, NotFoundError
from app.graph.build import get_graph
from app.graph.state import initial_state
from app.logging_config import get_logger

log = get_logger(__name__)

_HITL_NODES = {"learning_roadmap", "interview"}
# which human_feedback key each interrupt expects
_FEEDBACK_KEY = {"learning_roadmap": "skill_gap", "interview": "roadmap"}


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _snapshot(thread_id: str) -> dict:
    graph = get_graph()
    snap = graph.get_state(_config(thread_id))
    if not snap.created_at:
        raise NotFoundError(f"No session '{thread_id}'.")
    pending = list(snap.next)
    if not pending:
        status = "done"
        waiting_for = None
    elif set(pending) & _HITL_NODES:
        status = "interrupted"
        waiting_for = next(n for n in pending if n in _HITL_NODES)
    else:
        status = "running"
        waiting_for = None
    return {
        "thread_id": thread_id,
        "status": status,
        "waiting_for": waiting_for,
        "feedback_key": _FEEDBACK_KEY.get(waiting_for or ""),
        "state": snap.values,
    }


def start(resume_text: str, target_roles: list[str]) -> dict:
    thread_id = uuid.uuid4().hex
    graph = get_graph()
    graph.invoke(initial_state(thread_id, resume_text, target_roles), _config(thread_id))
    log.info("session %s started", thread_id)
    return _snapshot(thread_id)


def status(thread_id: str) -> dict:
    return _snapshot(thread_id)


def resume(thread_id: str, feedback: dict) -> dict:
    graph = get_graph()
    snap = _snapshot(thread_id)
    if snap["status"] != "interrupted":
        raise ConflictError(f"Session '{thread_id}' is '{snap['status']}', not awaiting input.")

    key = snap["feedback_key"]
    current = dict(snap["state"].get("human_feedback") or {})
    current[key] = feedback or {}
    graph.update_state(_config(thread_id), {"human_feedback": current})
    graph.invoke(None, _config(thread_id))
    log.info("session %s resumed past %s", thread_id, snap["waiting_for"])
    return _snapshot(thread_id)


def report(thread_id: str) -> str:
    snap = _snapshot(thread_id)
    return snap["state"].get("final_report") or "(report not ready — session still in progress)"
