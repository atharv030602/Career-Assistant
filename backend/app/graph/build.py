"""Assemble and compile the LangGraph state machine.

Flow:
    intake → resume_review → skill_gap
        └─(fit<55 & not revised)→ job_match → learning_roadmap
        └─(else)──────────────────────────→ learning_roadmap
    learning_roadmap → interview → synthesize → END

Human-in-the-loop: the graph interrupts *before* `learning_roadmap` (approve /
edit skill gaps) and *before* `interview` (pick timeline / focus topics).
"""

from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.config import settings
from app.graph import nodes
from app.graph.agents import interview, job_match, learning_roadmap, resume_review, skill_gap
from app.graph.state import CareerState
from app.logging_config import get_logger

log = get_logger(__name__)

INTERRUPT_BEFORE = ["learning_roadmap", "interview"]


def _checkpointer():
    if settings.checkpoint_backend.lower() == "sqlite":
        try:
            import sqlite3

            from langgraph.checkpoint.sqlite import SqliteSaver

            conn = sqlite3.connect(settings.checkpoint_db, check_same_thread=False)
            log.info("Checkpointer: SQLite (%s)", settings.checkpoint_db)
            return SqliteSaver(conn)
        except Exception as exc:  # pragma: no cover - optional dep
            log.warning("SqliteSaver unavailable (%s); using in-memory checkpointer.", exc)
    from langgraph.checkpoint.memory import MemorySaver

    log.info("Checkpointer: in-memory")
    return MemorySaver()


def _build() -> StateGraph:
    g = StateGraph(CareerState)
    g.add_node("intake", nodes.intake)
    g.add_node("resume_review", resume_review.run)
    g.add_node("skill_gap", skill_gap.run)
    g.add_node("job_match", job_match.run)
    g.add_node("learning_roadmap", learning_roadmap.run)
    g.add_node("interview", interview.run)
    g.add_node("synthesize", nodes.synthesize)

    g.add_edge(START, "intake")
    g.add_edge("intake", "resume_review")
    g.add_edge("resume_review", "skill_gap")
    g.add_conditional_edges(
        "skill_gap",
        nodes.route_after_gap,
        {"job_match": "job_match", "learning_roadmap": "learning_roadmap"},
    )
    g.add_edge("job_match", "learning_roadmap")
    g.add_edge("learning_roadmap", "interview")
    g.add_edge("interview", "synthesize")
    g.add_edge("synthesize", END)
    return g


@lru_cache(maxsize=1)
def get_graph():
    return _build().compile(checkpointer=_checkpointer(), interrupt_before=INTERRUPT_BEFORE)


def reset_graph() -> None:
    get_graph.cache_clear()


def active_checkpointer_name() -> str:
    name = type(get_graph().checkpointer).__name__
    return "sqlite" if "Sqlite" in name else "memory"
