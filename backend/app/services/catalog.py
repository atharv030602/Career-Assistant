"""Load + query the static role / resource catalogs."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_DATA = Path(__file__).resolve().parent.parent / "data"


@lru_cache(maxsize=1)
def roles() -> list[dict]:
    return json.loads((_DATA / "role_catalog.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def resources() -> dict[str, list[str]]:
    return json.loads((_DATA / "resource_catalog.json").read_text(encoding="utf-8"))


def find_role(name: str) -> dict | None:
    name_l = name.strip().lower()
    for r in roles():
        if r["role"].lower() == name_l:
            return r
    # loose contains match
    for r in roles():
        if name_l in r["role"].lower() or r["role"].lower() in name_l:
            return r
    return None


def required_skills(role_name: str) -> list[str]:
    role = find_role(role_name)
    if not role:
        return []
    return list(dict.fromkeys(role["core_skills"] + role.get("nice_to_have", [])))


def resources_for(skill: str) -> list[str]:
    return resources().get(skill, [f"Search: best free tutorial for {skill}"])
