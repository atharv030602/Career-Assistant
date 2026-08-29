# Multi-Agent Career Assistant

A **LangGraph** application where 5 specialised agents collaborate over typed
shared state to turn a resume + target role into a full plan: resume review,
skill-gap analysis, better-fit roles, a phased learning roadmap, and an
interview kit — with **human-in-the-loop checkpoints** you control.

Built to demonstrate: **LangGraph state machines · multi-agent orchestration ·
human-in-the-loop (interrupt / resume) · tool calling · conversation-thread
memory (checkpointer) · FastAPI · Streamlit · Docker · GitHub Actions CI ·
LangSmith**.

> **Runs with zero API keys.** Every agent has deterministic logic; an LLM
> (Gemini / OpenAI / OpenRouter) only *enriches* the output. Set a key to turn
> that on. The graph checkpointer defaults to in-memory (SQLite is opt-in via
> `requirements-sqlite.txt`).

```
career-assistant/
├── backend/    FastAPI + LangGraph (graph/, agents/, services/) + pytest
├── frontend/   Streamlit — run the agents, approve at each checkpoint
├── docs/       ARCHITECTURE (graph diagram), PLAN
└── docker-compose.yml · .github/workflows/ci.yml
```

## The graph

```
intake → resume_review → skill_gap
     ├─(fit < 55 & not revised)→ job_match ─┐
     └────────────────────────────────────┬─┴→ [HITL: approve gaps] → learning_roadmap
                                          → [HITL: pick timeline] → interview → synthesize → END
```

Full diagram + state schema + agent responsibilities: **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**.

## The 5 agents

| Agent | Does | Key tools |
|---|---|---|
| `resume_review` | strengths, red flags, stronger bullets | readability_scorer, quantification_checker, bullet_rewriter |
| `skill_gap` | matched/missing skills vs each role, weighted fit score | jd_keyword_extractor, skill_matcher |
| `job_match` | (low fit only) ranks better-fit catalog roles | role_catalog_lookup |
| `learning_roadmap` | phased plan from the **approved** gaps + your pace | effort_estimator, resource_catalog |
| `interview` | role-specific Q bank + STAR scaffolds | question_bank, star_scaffolder |

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/sessions` | start: `{resume_text, target_roles[]}` → runs to the first checkpoint |
| GET | `/api/sessions/{id}` | current state + `waiting_for` |
| POST | `/api/sessions/{id}/resume` | `{feedback: {...}}` → continue to the next checkpoint / end |
| GET | `/api/sessions/{id}/report` | final markdown report |
| GET | `/api/health` | provider / checkpointer / version |

`feedback` shape depends on `waiting_for`:
`learning_roadmap` → `{weekly_hours, priority_skills[], drop_skills[]}` ·
`interview` → `{focus_topics[]}`.

## Run it — local

```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt                        # core (LangGraph) — deterministic mode
pip install -r requirements-ai.txt                     # optional — LLM enrichment (Gemini/OpenAI/OpenRouter)
pip install -r requirements-dev.txt                    # tests + lint
cp .env.example .env                                   # optional: set LLM_PROVIDER + a key
uvicorn app.main:app --reload --port 8000              # http://localhost:8000/docs
```

```bash
cd frontend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
echo "API_BASE_URL=http://localhost:8000/api" > .env
streamlit run app.py                                   # http://localhost:8501
```

Quick test (no key):
```bash
curl -s localhost:8000/api/sessions -H 'content-type: application/json' -d '{
  "resume_text": "Backend engineer. Python, FastAPI, Docker, PostgreSQL, REST APIs, CI/CD.",
  "target_roles": ["GenAI Engineer"]
}' | python -m json.tool
```

## Run it — Docker

```bash
docker compose up --build       # backend :8000, frontend :8501 (in-memory checkpointer)
```
Put `OPENAI_API_KEY` (+ `OPENAI_BASE_URL` for OpenRouter) in a root `.env` to enable LLM enrichment.

## Tests & CI

```bash
cd backend && pip install -r requirements-dev.txt && pytest -q   # 15 tests, no network, no keys
ruff check app tests && ruff format --check app tests
```
GitHub Actions runs lint + format + tests + Docker builds on every push/PR to `main`.

## Enabling the LLM path

| Feature | Needs |
|---|---|
| LLM-enriched resume review (nuanced strengths / rewrites) | provider key + `requirements-ai.txt` |
| SQLite checkpointer (thread state survives restarts) | `requirements-sqlite.txt` + `CHECKPOINT_BACKEND=sqlite` (see the file's note) |
| LangSmith tracing of the graph run | `LANGSMITH_TRACING=true` + `LANGSMITH_API_KEY` |

`LLM_PROVIDER=openai` + `OPENAI_BASE_URL=https://openrouter.ai/api/v1` uses OpenRouter with any `openai/...` model.

## Deploying

Render (backend, Python runtime, `pip install -r requirements.txt -r requirements-ai.txt`,
`uvicorn app.main:app --host 0.0.0.0 --port $PORT`) + Streamlit Community Cloud
(frontend, `frontend/app.py`, secret `API_BASE_URL`). Same env vars as above.

## Roadmap

- `eval/` — LangSmith dataset + LLM-as-judge metrics (skill-gap recall,
  tool-selection accuracy, roadmap relevance). See `PLAN.md`.
- SSE streaming of node/token events.
- Supervisor-agent routing as an alternative to the fixed pipeline.

---

Project 2 of 3. Project 1: [ResumeFit AI 2.0](https://github.com/atharv030602/Resume-Analyzer) (RAG + tool-calling agent).
