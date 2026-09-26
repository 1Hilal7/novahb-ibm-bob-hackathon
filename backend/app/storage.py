"""
JSON file storage helpers for novaHB.

Thin wrappers around file read/write — no database, no ORM.
All paths are resolved relative to the repository root.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# Resolve the repository root (two levels up from backend/app/)
REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "config"
DATA_DIR = REPO_ROOT / "data"


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> Any:
    """Load and return JSON from *path*. Raises FileNotFoundError if missing."""
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path: Path, data: Any) -> None:
    """Serialise *data* to *path* as pretty-printed JSON."""
    _ensure_data_dir()
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Named accessors
# ---------------------------------------------------------------------------

def load_developers() -> list[dict]:
    return load_json(CONFIG_DIR / "developers.json")


def load_project_map() -> dict:
    return load_json(CONFIG_DIR / "project_map.json")


def load_impact_report() -> dict | None:
    path = DATA_DIR / "impact_report.json"
    if not path.exists():
        return None
    return load_json(path)


def save_impact_report(report: dict) -> None:
    save_json(DATA_DIR / "impact_report.json", report)


def load_reviews() -> list[dict]:
    path = DATA_DIR / "reviews.json"
    if not path.exists():
        return []
    return load_json(path)


def save_reviews(reviews: list[dict]) -> None:
    save_json(DATA_DIR / "reviews.json", reviews)
