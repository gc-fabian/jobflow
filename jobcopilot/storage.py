from __future__ import annotations
import json
from pathlib import Path
from .models import Job

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config.json"
DATA_PATH = ROOT / "data" / "jobs.json"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        example = ROOT / "config.example.json"
        return json.loads(example.read_text(encoding="utf-8"))
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def save_config(config: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def load_jobs() -> list[Job]:
    if not DATA_PATH.exists():
        return []
    raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return [Job.from_dict(item) for item in raw]


def save_jobs(jobs: list[Job]) -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps([j.to_dict() for j in jobs], ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        from .tracker import write_tracker
        write_tracker(ROOT, jobs)
    except Exception:
        # Tracker is a convenience view; never break data persistence because of markdown generation.
        pass
    try:
        from .sqlite_store import sync_if_exists
        sync_if_exists()
    except Exception:
        # SQLite is a derived mirror during migration; never block the canonical JSON write.
        pass


def next_id(jobs: list[Job]) -> int:
    return max([j.id for j in jobs], default=0) + 1
