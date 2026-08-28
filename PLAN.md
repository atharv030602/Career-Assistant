# Project 2 — Multi-Agent Career Assistant (LangGraph)

**Goal:** an enterprise-style LangGraph app where 5 specialised agents collaborate
over shared state, with human-in-the-loop checkpoints, tool calling, memory, an
evaluation harness, and production logging. Closes the keyword gaps Project 1
left open: **LangGraph, multi-agent orchestration, human-in-the-loop, state
management, agent evaluation.**

Repo: `career-assistant/` (sibling of `resumefit-ai/`, its own GitHub repo).

---

## 1. The graph

`StateGraph(CareerState)` — a mostly-sequential pipeline with two conditional
edges and two HITL interrupts.

```
        ┌─────────────────┐
        │  intake (node)  │  parse resume + target role(s), normalise
        └────────┬────────┘
                 ▼
     ┌───────────────────────┐
     │  resume_review_agent  │  strengths, red flags, bullet rewrites
     └───────────┬───────────┘
                 ▼
     ┌───────────────────────┐
     │   skill_gap_agent     │  matched / missing skills vs role, ranked
     └───────────┬───────────┘
                 ▼
        ╔═══════════════════╗
        ║  HITL interrupt   ║  user edits/approves the skill-gap list
        ╚═════════╤═════════╝
                 ▼
        ┌──────── router ────────┐  conditional edge on fit_score
        │  < 55  → job_match     │  (suggest better-fit roles, then re-loop once)
        │  ≥ 55  → roadmap       │
        └──────────┬─────────────┘
                 ▼
     ┌───────────────────────┐
     │ learning_roadmap_agent│  phased plan, resources, time estimates
     └───────────┬───────────┘
                 ▼
        ╔═══════════════════╗
        ║  HITL interrupt   ║  user picks timeline / priorities
        ╚═════════╤═════════╝
                 ▼
     ┌───────────────────────┐
     │   interview_agent     │  role-specific Q bank + STAR answer scaffolds
     └───────────┬───────────┘
                 ▼
        ┌─────────────────┐
        │  synthesize     │  final report (markdown) + per-agent artifacts
        └─────────────────┘
```

- **Checkpointer:** `MemorySaver` locally; `SqliteSaver` (file) for the deployed
  demo so a `thread_id` survives restarts. State + HITL resume both key off
  `thread_id`.
- **Interrupts:** `interrupt_before=["learning_roadmap_agent", "interview_agent"]`
  (or `interrupt()` inside the node). The API exposes a `/resume` endpoint that
  feeds human input back in.
- **job_match loop:** cap at 1 re-entry (guard with a `revisions` counter in state)
  so it can't spin.

---

## 2. Shared state

```python
class CareerState(TypedDict):
    thread_id: str
    resume_text: str
    target_roles: list[str]
    # filled by agents
    resume_review: ResumeReview | None
    skill_gaps: list[SkillGap]
    fit_score: int
    job_matches: list[JobMatch]
    roadmap: Roadmap | None
    interview_kit: InterviewKit | None
    final_report: str
    # control
    revisions: int
    human_feedback: dict[str, Any]   # keyed by node name
    messages: Annotated[list, add_messages]   # audit trail
```

Each agent reads what it needs, writes exactly one slice, appends to `messages`.

---

## 3. The 5 agents

| Agent | Input | Tools | Output slice |
|---|---|---|---|
| **resume_review_agent** | `resume_text` | `bullet_rewriter`, `readability_scorer`, `quantification_checker` | `resume_review` (strengths, flags, 5 rewritten bullets) |
| **skill_gap_agent** | `resume_text`, `target_roles` | `jd_keyword_extractor`, `skill_matcher` (port from Project 1's `local_matcher`), `semantic_similarity` | `skill_gaps` (ranked, importance), `fit_score` |
| **job_match_agent** | `resume_review`, `skill_gaps`, `fit_score` | `role_catalog_lookup` (static JSON of ~30 roles + skill profiles), `role_similarity` | `job_matches` (3–5 roles + why) |
| **learning_roadmap_agent** | approved `skill_gaps`, `human_feedback["skill_gap"]` | `resource_catalog` (curated courses/docs JSON), `effort_estimator` | `roadmap` (phases, weekly hours, milestones) |
| **interview_agent** | `target_roles`, `skill_gaps`, `roadmap` | `question_bank` (by topic), `star_scaffolder` | `interview_kit` (10–15 Qs, 3 worked STAR answers) |

- Each agent = `langchain.agents.create_agent(model, tools, system_prompt)` wrapped
  in a graph node; node reconciles the agent's tool outputs into the typed slice.
- Deterministic fallback: if no API key, each agent runs its tools in a fixed
  order and templates the output (same graceful-degradation pattern as Project 1).

---

## 4. Reuse from Project 1 (copy, don't import)

- `app/core/llm.py` — provider factory (Gemini / OpenAI / OpenRouter via
  `OPENAI_BASE_URL`), `configure_langsmith()`.
- `app/core/errors.py`, `app/logging_config.py` (request-id + JSON logs).
- `app/services/local_matcher.py` + `skills_data.py` → becomes the
  `skill_matcher` tool.
- `app/services/embeddings_service.py` (hashing fallback).
- `ruff.toml`, `pytest.ini`, Dockerfile pattern, `.github/workflows/ci.yml`.

---

## 5. Folder structure

```
career-assistant/
├── backend/
│   ├── app/
│   │   ├── main.py                 FastAPI app factory
│   │   ├── config.py
│   │   ├── core/                   llm.py, errors.py
│   │   ├── logging_config.py
│   │   ├── graph/
│   │   │   ├── state.py            CareerState + typed slices
│   │   │   ├── build.py            StateGraph wiring, checkpointer, interrupts
│   │   │   ├── nodes.py            intake / router / synthesize
│   │   │   └── agents/
│   │   │       ├── resume_review.py
│   │   │       ├── skill_gap.py
│   │   │       ├── job_match.py
│   │   │       ├── learning_roadmap.py
│   │   │       ├── interview.py
│   │   │       └── tools.py        all agent tools (plain fns + StructuredTool)
│   │   ├── routers/
│   │   │   ├── health.py
│   │   │   └── sessions.py         start / status / resume / report
│   │   ├── data/
│   │   │   ├── role_catalog.json
│   │   │   └── resource_catalog.json
│   │   └── services/               local_matcher, embeddings, report_render
│   ├── eval/
│   │   ├── dataset.jsonl           ~15 (resume, target_roles, expected) rows
│   │   ├── metrics.py              completion, tool-accuracy, judge scores
│   │   └── run_eval.py             LangSmith evaluate() + local JSON report
│   ├── tests/
│   ├── requirements.txt / -ai.txt / -dev.txt
│   ├── Dockerfile
│   └── ruff.toml / pytest.ini
├── frontend/
│   ├── app.py                      Streamlit — start run, see per-agent output,
│   │                               approve/edit at HITL points, download report
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml              backend + frontend (+ optional sqlite volume)
├── .github/workflows/ci.yml
├── docs/
│   ├── ARCHITECTURE.md             graph diagram + agent comms + state
│   ├── EVALUATION.md               harness, metrics table, results
│   └── RESUME_BULLETS.md
└── README.md
```

---

## 6. API surface (FastAPI)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/sessions` | start a run: `{resume_text, target_roles}` → `{thread_id, status}` (runs until first interrupt) |
| GET | `/api/sessions/{thread_id}` | current state snapshot + which node is waiting |
| POST | `/api/sessions/{thread_id}/resume` | `{node, feedback}` → continues the graph to the next interrupt / end |
| GET | `/api/sessions/{thread_id}/report` | final markdown report + artifacts |
| GET | `/api/health` | provider / checkpointer / version |

Graph runs are sync per step; each `POST` returns when the graph next interrupts
or finishes. (Optional stretch: SSE streaming of node/token events.)

---

## 7. Frontend (Streamlit)

- **Start panel:** resume paste/upload + target roles (multi-select or free text).
- **Timeline view:** one expander per agent, fills in as the graph progresses;
  show the `messages` audit trail + which tools each agent called.
- **HITL cards:** when `status == "interrupted"`, render an editable form for the
  waiting node (edit skill-gap list / pick timeline) → `POST /resume`.
- **Report tab:** rendered markdown + download button.
- Session id in `st.session_state`, same as Project 1.

---

## 8. Evaluation framework (`eval/`)

Dataset: ~15 rows of `{resume_text, target_roles, expected_missing_skills,
expected_role_family}`.

Metrics:
| Metric | How |
|---|---|
| graph completion rate | ran end-to-end without error / N |
| skill-gap recall | overlap(predicted_missing, expected_missing) |
| tool-selection accuracy | each agent called its expected tools ≥ once |
| roadmap relevance | LLM-as-judge (1–5) on roadmap vs skill gaps |
| interview-kit coverage | judge: do questions cover the top-3 gaps? |
| latency / est. cost | per run, logged |

Runner: `python -m eval.run_eval` → writes `eval/report.json` + prints a table;
also register the dataset in LangSmith and use `evaluate()` for the judge metrics
so it shows in the LangSmith UI. Document results in `docs/EVALUATION.md`.

---

## 9. Infra

- **Dockerfile** (python:3.12-slim), pure-Python AI stack in `requirements-ai.txt`
  (`langchain`, `langgraph`, `langchain-openai`, `langchain-google-genai`,
  `langsmith`); no chromadb needed (no RAG store in this project — memory is the
  checkpointer).
- **docker-compose.yml:** backend + frontend, sqlite checkpointer on a volume.
- **CI:** ruff check + format + pytest (deterministic, no keys) + docker build.
- **Deploy:** Render (backend, Python runtime, `pip install -r requirements.txt
  -r requirements-ai.txt`, `uvicorn app.main:app`) + Streamlit Cloud (frontend,
  `frontend/app.py`, secret `API_BASE_URL`). Same env vars as Project 1:
  `LLM_PROVIDER=openai`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`,
  `OPENAI_CHAT_MODEL=openai/gpt-4o-mini`, `LANGSMITH_TRACING=true` + key.

---

## 10. Build order (≈ the sessions)

1. **Scaffold** — folder, config, `core/llm.py` + logging copied, FastAPI health,
   ruff/pytest/CI, empty graph that runs `intake → synthesize`. Deployable.
2. **State + 2 agents** — `CareerState`, `resume_review_agent`,
   `skill_gap_agent` (+ ported tools), sequential graph, tests. No HITL yet.
3. **HITL + checkpointer** — `SqliteSaver`, `interrupt_before`, `/sessions` +
   `/resume` endpoints, `thread_id` lifecycle. Test interrupt→resume.
4. **Remaining 3 agents + router** — `job_match`, `learning_roadmap`,
   `interview`, conditional edge + revision guard, `synthesize` report renderer.
5. **Streamlit UI** — timeline view, HITL forms, report tab.
6. **Eval harness** — dataset, metrics, `run_eval.py`, LangSmith datasets,
   `docs/EVALUATION.md` with a results table.
7. **Polish + deploy** — `docs/ARCHITECTURE.md` (Mermaid graph), README,
   `RESUME_BULLETS.md`, deploy backend + frontend, smoke test, LinkedIn post.

---

## 11. Resume bullets this unlocks

- Built a **5-agent LangGraph system** with typed shared state, conditional
  routing, and a bounded revision loop; agents collaborate via a reducer-based
  state channel with a full message audit trail.
- Implemented **human-in-the-loop checkpoints** using LangGraph interrupts + a
  SQLite checkpointer, exposing pause/resume over a FastAPI `/sessions/{id}/resume`
  endpoint keyed by `thread_id`.
- Created an **agent evaluation harness** (LangSmith datasets + LLM-as-judge):
  skill-gap recall, tool-selection accuracy, roadmap relevance, latency/cost —
  results tracked per release.
- Reused a **provider-agnostic LLM layer** (Gemini / OpenAI / OpenRouter) with
  deterministic fallback so the graph runs and is testable with zero API keys.
- Shipped with **Docker Compose, GitHub Actions CI, and LangSmith tracing**;
  deployed backend on Render + Streamlit UI on Streamlit Cloud.

---

## Open decisions (pick tomorrow)

- **Router style:** fixed sequential + 1 conditional (this plan) vs a supervisor
  agent that dynamically routes. Sequential is easier to diagram/evaluate — start
  there, mention the supervisor pattern as "future work".
- **Job data:** static `role_catalog.json` (recommended, zero external deps) vs a
  live jobs API. Static keeps CI/deploy clean.
- **Streaming:** add SSE token/node streaming as a stretch goal, not v1.
