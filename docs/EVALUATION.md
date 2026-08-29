# Evaluation

`backend/eval/` is a small, reproducible harness that runs the whole LangGraph
pipeline over a labelled dataset and scores each run.

```bash
cd backend
python -m eval.run_eval               # deterministic metrics + LLM judge if a key is set
python -m eval.run_eval --no-judge    # deterministic only (what CI runs)
LANGSMITH_API_KEY=... python -m eval.langsmith_eval   # optional: push to LangSmith + evaluate()
```

Output: a per-case table, an aggregate block, and `eval/report.json`.

## Dataset — `eval/dataset.jsonl`

12 hand-labelled cases across GenAI / Backend / ML / Data / DevOps / Full-stack /
Cloud / MLOps roles, each with:

| field | meaning |
|---|---|
| `resume_text`, `target_roles` | graph inputs |
| `expected_missing` | skills the résumé lacks that the role needs → **recall** |
| `expected_present` | skills the résumé clearly has → **precision** (must not be flagged missing) |
| `expect_job_match` | whether fit should fall below 55 and the router should invoke `job_match` → **routing accuracy** |

## Metrics — `eval/metrics.py`

| Metric | How it's computed |
|---|---|
| **completion_rate** | graph reached `final_report` with no exception and no pending node |
| **routing_accuracy** | `job_match_agent` ran **iff** `expect_job_match` |
| **node_coverage** | fraction of the 6 core nodes present in the run trace |
| **skill_gap_recall** | \|predicted ∩ expected_missing\| / \|expected_missing\| (canonicalised) |
| **skill_gap_precision** | 1 − (predicted ∩ expected_present) / \|expected_present\| — false-positive rate against known-present skills |
| **roadmap_covers_high_gaps** | fraction of *high*-importance gaps that appear in a roadmap phase's `focus_skills` |
| **interview_covers_top_gaps** | fraction of the top-3 gaps referenced in the interview questions |
| **judge_roadmap_1_5**, **judge_interview_1_5** | LLM-as-judge (1–5) with a strict rubric — only when a provider key is set |
| **p50_latency_ms** | median wall-clock per full graph run |

Deterministic metrics need no network; `run_eval` runs them in CI with no keys.

## Results

Deterministic mode (no API key) — `python -m eval.run_eval --no-judge`, 12 cases:

| Aggregate | Value |
|---|---|
| completion_rate | **1.00** |
| routing_accuracy | **1.00** |
| mean_node_coverage | **1.00** |
| mean_skill_gap_recall | **1.00** |
| mean_skill_gap_precision | **1.00** |
| mean_roadmap_covers_high_gaps | **1.00** |
| mean_interview_covers_top_gaps | **0.89** |
| p50_latency_ms | **~21 ms** |

AI mode (OpenRouter `openai/gpt-4o-mini`, `resume_review` uses the LLM path):
same structural metrics, p50 latency **~3.8 s** per run, judge scores populated.

### Reading these numbers honestly

The dataset labels are authored to match the intended behaviour of the
deterministic matcher, so recall / precision near 1.0 **confirm the pipeline and
routing haven't regressed** rather than proving open-world accuracy. The
`interview_covers_top_gaps` gap (0.89) is a real weak spot — a few runs phrase a
question around a skill without naming it literally. The durable value here is
the **harness, the metric design, the reproducible `report.json`, and the
LangSmith `evaluate()` hook** — run it on every change to catch graph / routing /
prompt regressions.

## CI

`test_eval.py` runs the harness on the dataset (deterministic) as part of the
normal `pytest` job — a graph or routing regression fails the build.

## Next

- Grow the dataset to ~40 cases, including adversarial résumés (keyword-stuffed, wrong-domain).
- Add a **trajectory** metric: assert the exact node order per case, not just presence.
- Wire `langsmith_eval.py` into a nightly GitHub Action once a LangSmith key is available.
