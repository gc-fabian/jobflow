from __future__ import annotations

import json
from datetime import datetime, timezone

from jobcopilot.models import Job


def test_scan_counts_existing_job_once_per_run(monkeypatch, tmp_path):
    from jobcopilot import scanner
    from jobcopilot import sqlite_store

    now = datetime.now(timezone.utc).isoformat()
    existing = Job(
        id=1,
        company="Acme",
        role="Backend Developer",
        url="https://www.getonbrd.comhttps://www.getonbrd.com/jobs/backend",
        source="seed",
        description="Python Node React backend developer",
        score=10,
        created_at=now,
        updated_at=now,
    )
    sources = {
        "searches": [
            {"name": "GetOnBoard - A", "url": "https://www.getonbrd.com/empleos/programacion", "login_required": False},
            {"name": "GetOnBoard - B", "url": "https://www.getonbrd.com/empleos/programacion", "login_required": False},
        ],
        "target_companies": ["Acme"],
    }
    config = {
        "must_have_keywords": ["backend"],
        "preferred_roles": ["developer"],
        "avoid_keywords": [],
    }
    html = '<html><title>Jobs</title><a href="https://www.getonbrd.com/jobs/backend">Backend Developer Acme</a></html>'
    saved_jobs = []

    monkeypatch.setattr(scanner, "SOURCES_PATH", tmp_path / "sources.json")
    monkeypatch.setattr(scanner, "LAST_SCAN_PATH", tmp_path / "last_scan.json")
    scanner.SOURCES_PATH.write_text(json.dumps(sources), encoding="utf-8")
    monkeypatch.setattr(scanner, "load_config", lambda: config)
    monkeypatch.setattr(scanner, "load_jobs", lambda: [existing])

    def fake_save_jobs(jobs):
        saved_jobs[:] = jobs

    monkeypatch.setattr(scanner, "save_jobs", fake_save_jobs)
    monkeypatch.setattr(scanner, "_fetch_html", lambda url, timeout=20: ("Jobs", html, "Backend Developer Acme Python Node"))
    monkeypatch.setattr(sqlite_store, "sync_if_exists", lambda: None)

    result = scanner.run_scan(limit_per_source=10)

    assert result["updated"] == 1
    assert result["added"] == 0
    assert len(saved_jobs) == 1
    assert saved_jobs[0].last_seen_at == result["scanned_at"]
    assert any(event["status"] == "seen" for event in result["events"])
