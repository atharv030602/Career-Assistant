"""Run the eval suite over the dataset and write a report.

    python -m eval.run_eval               # deterministic + LLM judge if a key is set
    python -m eval.run_eval --no-judge    # deterministic metrics only
    python -m eval.run_eval --out eval/report.json

Writes eval/report.json and prints a per-case + aggregate table. When
LANGSMITH_TRACING=true every graph run also shows up in the LangSmith UI.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from app.core.llm import ai_enabled, configure_langsmith
from eval import metrics
from eval.cases import load_cases
from eval.harness import run_case

_REPORT = Path(__file__).resolve().parent / "report.json"


def _mean(values: list[float | None]) -> float | None:
    nums = [v for v in values if isinstance(v, (int, float))]
    return round(statistics.mean(nums), 3) if nums else None


def evaluate(use_judge: bool) -> dict:
    configure_langsmith()
    cases = load_cases()
    rows: list[dict] = []

    for case in cases:
        run = run_case(case.resume_text, case.target_roles, case.id)
        s = run.state
        row = {
            "id": case.id,
            "completed": run.ok,
            "latency_ms": run.latency_ms,
            "ai_powered": bool(s.get("ai_powered")),
            "fit_score": s.get("fit_score"),
            "skill_gap_recall": metrics.skill_gap_recall(s, case.expected_missing),
            "skill_gap_precision": metrics.skill_gap_precision_against_present(
                s, case.expected_present
            ),
            "routing_correct": metrics.routing_correct(s, case.expect_job_match),
            "node_coverage": metrics.node_coverage(s),
            "roadmap_covers_high_gaps": metrics.roadmap_covers_high_gaps(s),
            "interview_covers_top_gaps": metrics.interview_covers_top_gaps(s),
            "error": run.error,
        }
        if use_judge and ai_enabled():
            jr = metrics.judge_roadmap_relevance(s)
            ji = metrics.judge_interview_quality(s)
            row["judge_roadmap_1_5"] = jr["score"] if jr else None
            row["judge_interview_1_5"] = ji["score"] if ji else None
        rows.append(row)

    agg = {
        "cases": len(rows),
        "completion_rate": round(sum(r["completed"] for r in rows) / len(rows), 3),
        "routing_accuracy": round(sum(r["routing_correct"] for r in rows) / len(rows), 3),
        "mean_node_coverage": _mean([r["node_coverage"] for r in rows]),
        "mean_skill_gap_recall": _mean([r["skill_gap_recall"] for r in rows]),
        "mean_skill_gap_precision": _mean([r["skill_gap_precision"] for r in rows]),
        "mean_roadmap_covers_high_gaps": _mean([r["roadmap_covers_high_gaps"] for r in rows]),
        "mean_interview_covers_top_gaps": _mean([r["interview_covers_top_gaps"] for r in rows]),
        "p50_latency_ms": round(statistics.median(r["latency_ms"] for r in rows), 1),
    }
    if use_judge and ai_enabled():
        agg["mean_judge_roadmap_1_5"] = _mean([r.get("judge_roadmap_1_5") for r in rows])
        agg["mean_judge_interview_1_5"] = _mean([r.get("judge_interview_1_5") for r in rows])

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "ai_powered": ai_enabled(),
        "judge_used": bool(use_judge and ai_enabled()),
        "aggregate": agg,
        "cases_detail": rows,
    }


def _print_table(report: dict) -> None:
    rows = report["cases_detail"]
    cols = [
        "id",
        "completed",
        "fit_score",
        "skill_gap_recall",
        "skill_gap_precision",
        "routing_correct",
        "roadmap_covers_high_gaps",
        "interview_covers_top_gaps",
        "latency_ms",
    ]
    widths = {c: max(len(c), *(len(str(r.get(c))) for r in rows)) for c in cols}
    print(" | ".join(c.ljust(widths[c]) for c in cols))
    print("-+-".join("-" * widths[c] for c in cols))
    for r in rows:
        print(" | ".join(str(r.get(c)).ljust(widths[c]) for c in cols))
    print("\nAGGREGATE")
    for k, v in report["aggregate"].items():
        print(f"  {k:34} {v}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-judge", action="store_true", help="skip LLM-as-judge metrics")
    ap.add_argument("--out", default=str(_REPORT))
    args = ap.parse_args()

    report = evaluate(use_judge=not args.no_judge)
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    _print_table(report)
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
