# Architecture — Multi-Agent Career Assistant

## Graph

```
              ┌────────┐
   START ───▶ │ intake │  normalise resume + target_roles
              └───┬────┘
                  ▼
        ┌──────────────────┐
        │ resume_review    │  strengths · red flags · rewritten bullets
        └────────┬─────────┘
                 ▼
        ┌──────────────────┐
        │ skill_gap        │  matched/missing per role · weighted fit_score
        └────────┬─────────┘
                 │  route_after_gap(state)
        fit<55 & revisions==0 │ else
                 ▼             │
        ┌──────────────────┐   │
        │ job_match        │   │  rank better-fit catalog roles; revisions += 1
        └────────┬─────────┘   │
                 └─────────────┤
                               ▼
                    ╔═══════════════════════╗
                    ║ interrupt_before      ║  HITL #1 — approve / edit skill gaps,
                    ║ "learning_roadmap"    ║  set weekly_hours, drop/prioritise
                    ╚══════════╤════════════╝
                               ▼
                    ┌──────────────────────┐
                    │ learning_roadmap     │  phased plan from approved gaps
                    └──────────┬───────────┘
                               ▼
                    ╔═══════════════════════╗
                    ║ interrupt_before      ║  HITL #2 — pick interview focus topics
                    ║ "interview"           ║
                    ╚══════════╤════════════╝
                               ▼
                    ┌──────────────────────┐
                    │ interview            │  Q bank + STAR scaffolds
                    └──────────┬───────────┘
                               ▼
                    ┌──────────────────────┐
                    │ synthesize → END     │  render final markdown report
                    └──────────────────────┘
```

Compiled with `StateGraph(CareerState).compile(checkpointer=..., interrupt_before=["learning_roadmap", "interview"])`.

## State (`app/graph/state.py`)

`CareerState` is a `TypedDict` (total=False). Each agent returns a **partial**
dict; LangGraph merges it. `trace` uses an `operator.add` reducer so every node
appends its line. Typed Pydantic slices: `ResumeReview`, `SkillGap`, `JobMatch`,
`Roadmap`/`RoadmapPhase`, `InterviewKit`/`InterviewQuestion`.

Control fields: `revisions` (caps the job_match loop at 1), `human_feedback`
(dict keyed by the interrupt's feedback key — `skill_gap` / `roadmap`).

## Human-in-the-loop lifecycle

```
POST /api/sessions            graph.invoke(initial_state, {thread_id})
                              → runs until interrupt_before "learning_roadmap"
GET  /api/sessions/{id}       graph.get_state(config) → .next tells you the pending node
POST /api/sessions/{id}/resume
                              merge feedback into state via graph.update_state(...)
                              graph.invoke(None, config)   # continue
                              → next interrupt ("interview") or END
GET  /api/sessions/{id}/report   state["final_report"]
```

`thread_id` is the checkpoint key. `session_service._snapshot` maps `snap.next`
→ status (`running` / `interrupted` / `done`) and the expected feedback key.

## Agent pattern

Every agent is `run(state: dict) -> dict`:
1. deterministic core using pure tools in `graph/agents/tools.py` (unit-tested, no network);
2. if `ai_enabled()`, call `core.llm.llm_json(system, user)` and merge the parsed
   result — any failure (no key, bad JSON, timeout) falls back to the
   deterministic output. `resume_review` implements the LLM path; the others
   have the same seam.

## Provider layer (`app/core/llm.py`)

`LLM_PROVIDER=gemini|openai`. `openai` + `OPENAI_BASE_URL` targets any
OpenAI-compatible gateway (OpenRouter). LangChain imports are lazy so the app
boots without the AI stack. `llm_json()` is the only entry point the agents use.

## Checkpointer (`app/graph/build.py`)

Defaults to `MemorySaver` (`CHECKPOINT_BACKEND=memory`). `CHECKPOINT_BACKEND=sqlite`
→ `SqliteSaver` (needs `requirements-sqlite.txt`; its releases currently lag
langgraph 1.x, so it's opt-in) — and still falls back to `MemorySaver` if the
import fails. `active_checkpointer_name()` reports what's live.

## Static data (`app/data/`)

`role_catalog.json` — ~10 roles with `core_skills` + `nice_to_have`.
`resource_catalog.json` — skill → curated free learning resources.
Both loaded + cached in `services/catalog.py`.
