"""Load the eval dataset."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

_DATASET = Path(__file__).resolve().parent / "dataset.jsonl"


@dataclass
class EvalCase:
    id: str
    resume_text: str
    target_roles: list[str]
    expected_missing: list[str] = field(default_factory=list)
    expected_present: list[str] = field(default_factory=list)
    expect_job_match: bool = False


def load_cases() -> list[EvalCase]:
    cases: list[EvalCase] = []
    for line in _DATASET.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        raw = json.loads(line)
        cases.append(
            EvalCase(
                id=raw["id"],
                resume_text=raw["resume_text"],
                target_roles=raw["target_roles"],
                expected_missing=raw.get("expected_missing", []),
                expected_present=raw.get("expected_present", []),
                expect_job_match=raw.get("expect_job_match", False),
            )
        )
    return cases
