from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .acquisition import canonical_url, classify_source
from .models import Job
from .storage import DATA_PATH, ROOT, load_config, load_jobs
from .scanner import LAST_SCAN_PATH, SOURCES_PATH

DB_PATH = ROOT / "data" / "jobflow.sqlite"
SCHEMA_VERSION = 1


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS candidates (
            id TEXT PRIMARY KEY,
            name TEXT,
            email TEXT,
            headline TEXT,
            profile_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            url TEXT,
            source_type TEXT NOT NULL,
            login_required INTEGER NOT NULL DEFAULT 0,
            enabled INTEGER NOT NULL DEFAULT 1,
            priority INTEGER NOT NULL DEFAULT 0,
            config_json TEXT NOT NULL DEFAULT '{}',
            last_scan_at TEXT,
            last_error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            normalized_name TEXT NOT NULL,
            careers_url TEXT,
            linkedin_url TEXT,
            country TEXT,
            industry TEXT,
            evidence_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY,
            canonical_url TEXT NOT NULL UNIQUE,
            company_id INTEGER,
            company TEXT NOT NULL,
            role TEXT NOT NULL,
            source_id INTEGER,
            source_name TEXT NOT NULL,
            source_type TEXT NOT NULL,
            channel TEXT NOT NULL,
            location TEXT,
            description TEXT,
            status TEXT NOT NULL,
            score INTEGER NOT NULL DEFAULT 0,
            reasons_json TEXT NOT NULL DEFAULT '[]',
            risks_json TEXT NOT NULL DEFAULT '[]',
            raw_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_seen_at TEXT,
            FOREIGN KEY(company_id) REFERENCES companies(id),
            FOREIGN KEY(source_id) REFERENCES sources(id)
        );

        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT,
            finished_at TEXT,
            mode TEXT NOT NULL DEFAULT 'import',
            scanned INTEGER NOT NULL DEFAULT 0,
            skipped_login INTEGER NOT NULL DEFAULT 0,
            added INTEGER NOT NULL DEFAULT 0,
            updated INTEGER NOT NULL DEFAULT 0,
            ignored_listing_pages INTEGER NOT NULL DEFAULT 0,
            errors_json TEXT NOT NULL DEFAULT '[]',
            summary_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS scan_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id INTEGER NOT NULL,
            status TEXT,
            stage TEXT,
            message TEXT,
            source_name TEXT,
            url TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY(scan_id) REFERENCES scans(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS raw_observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER,
            job_id INTEGER,
            canonical_url TEXT,
            raw_url TEXT,
            raw_title TEXT,
            raw_text TEXT,
            content_hash TEXT,
            fetch_status TEXT NOT NULL DEFAULT 'imported',
            observed_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY(source_id) REFERENCES sources(id),
            FOREIGN KEY(job_id) REFERENCES jobs(id)
        );

        CREATE TABLE IF NOT EXISTS job_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            candidate_id TEXT NOT NULL,
            score INTEGER NOT NULL,
            reasons_json TEXT NOT NULL DEFAULT '[]',
            risks_json TEXT NOT NULL DEFAULT '[]',
            recommendation TEXT NOT NULL DEFAULT 'review',
            created_at TEXT NOT NULL,
            FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE,
            FOREIGN KEY(candidate_id) REFERENCES candidates(id)
        );

        CREATE INDEX IF NOT EXISTS idx_jobs_status_score ON jobs(status, score DESC);
        CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source_id, last_seen_at);
        CREATE INDEX IF NOT EXISTS idx_jobs_company_role ON jobs(company, role);
        CREATE INDEX IF NOT EXISTS idx_jobs_last_seen ON jobs(last_seen_at);
        CREATE INDEX IF NOT EXISTS idx_raw_observations_url ON raw_observations(canonical_url);
        CREATE INDEX IF NOT EXISTS idx_scan_events_scan ON scan_events(scan_id, stage, status);
        """
    )
    conn.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES('schema_version', ?)",
        (str(SCHEMA_VERSION),),
    )
    conn.commit()


def _upsert_candidate(conn: sqlite3.Connection, candidate: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO candidates(id, name, email, headline, profile_json, updated_at)
        VALUES('fabian', ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
          name=excluded.name,
          email=excluded.email,
          headline=excluded.headline,
          profile_json=excluded.profile_json,
          updated_at=excluded.updated_at
        """,
        (
            candidate.get("name", ""),
            candidate.get("email", ""),
            candidate.get("headline") or candidate.get("base_profile", ""),
            _json(candidate),
            utc_now(),
        ),
    )


def _source_type_for_config(source: dict[str, Any]) -> str:
    if source.get("login_required"):
        return "manual_login"
    return classify_source(source.get("name", ""), "", source.get("url", ""))


def _upsert_source(conn: sqlite3.Connection, source: dict[str, Any]) -> int:
    now = utc_now()
    name = source.get("name") or source.get("url") or "fuente sin nombre"
    conn.execute(
        """
        INSERT INTO sources(name, url, source_type, login_required, enabled, priority, config_json, created_at, updated_at)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
          url=excluded.url,
          source_type=excluded.source_type,
          login_required=excluded.login_required,
          enabled=excluded.enabled,
          priority=excluded.priority,
          config_json=excluded.config_json,
          updated_at=excluded.updated_at
        """,
        (
            name,
            source.get("url", ""),
            _source_type_for_config(source),
            1 if source.get("login_required") else 0,
            0 if source.get("enabled") is False else 1,
            int(source.get("priority") or 0),
            _json(source),
            now,
            now,
        ),
    )
    row = conn.execute("SELECT id FROM sources WHERE name = ?", (name,)).fetchone()
    return int(row["id"])


def _upsert_company(conn: sqlite3.Connection, name: str) -> int | None:
    clean = (name or "").strip()
    if not clean or clean.startswith("[COMPLETAR"):
        return None
    now = utc_now()
    normalized = " ".join(clean.lower().split())
    conn.execute(
        """
        INSERT INTO companies(name, normalized_name, created_at, updated_at)
        VALUES(?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
          normalized_name=excluded.normalized_name,
          updated_at=excluded.updated_at
        """,
        (clean, normalized, now, now),
    )
    row = conn.execute("SELECT id FROM companies WHERE name = ?", (clean,)).fetchone()
    return int(row["id"]) if row else None


def _source_id_by_name(conn: sqlite3.Connection, name: str, job: Job) -> int:
    row = conn.execute("SELECT id FROM sources WHERE name = ?", (name,)).fetchone()
    if row:
        return int(row["id"])
    return _upsert_source(
        conn,
        {
            "name": name or "unknown",
            "url": job.url,
            "login_required": classify_source(name, job.channel, job.url) == "manual_login",
            "priority": 0,
        },
    )


def _recommendation(job: Job) -> str:
    if job.status == "discarded" or job.score < 0:
        return "discard"
    if job.score >= 70:
        return "prepare"
    if job.score >= 35:
        return "review"
    return "low_priority"


def _upsert_job(conn: sqlite3.Connection, job: Job) -> None:
    url = canonical_url(job.url) or f"manual:{job.id}"
    source_id = _source_id_by_name(conn, job.source or "unknown", job)
    source_type = classify_source(job.source or "", job.channel or "", job.url or "")
    company_id = _upsert_company(conn, job.company)
    conn.execute(
        """
        INSERT INTO jobs(
          id, canonical_url, company_id, company, role, source_id, source_name, source_type, channel,
          location, description, status, score, reasons_json, risks_json, raw_json,
          created_at, updated_at, last_seen_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(canonical_url) DO UPDATE SET
          company_id=excluded.company_id,
          company=excluded.company,
          role=excluded.role,
          source_id=excluded.source_id,
          source_name=excluded.source_name,
          source_type=excluded.source_type,
          channel=excluded.channel,
          location=excluded.location,
          description=excluded.description,
          status=excluded.status,
          score=excluded.score,
          reasons_json=excluded.reasons_json,
          risks_json=excluded.risks_json,
          raw_json=excluded.raw_json,
          updated_at=excluded.updated_at,
          last_seen_at=excluded.last_seen_at
        """,
        (
            job.id,
            url,
            company_id,
            job.company,
            job.role,
            source_id,
            job.source or "unknown",
            source_type,
            job.channel,
            job.location,
            job.description,
            job.status,
            int(job.score or 0),
            _json(job.reasons),
            _json(job.risks),
            _json(job.to_dict()),
            job.created_at or utc_now(),
            job.updated_at or utc_now(),
            job.last_seen_at or job.updated_at or utc_now(),
        ),
    )
    conn.execute(
        """
        INSERT INTO raw_observations(source_id, job_id, canonical_url, raw_url, raw_title, raw_text, fetch_status, observed_at, metadata_json)
        VALUES(?, ?, ?, ?, ?, ?, 'imported', ?, ?)
        """,
        (
            source_id,
            job.id,
            url,
            job.url,
            job.role,
            job.description,
            job.last_seen_at or job.updated_at or utc_now(),
            _json({"imported_from": "data/jobs.json", "channel": job.channel}),
        ),
    )
    conn.execute(
        """
        INSERT INTO job_matches(job_id, candidate_id, score, reasons_json, risks_json, recommendation, created_at)
        VALUES(?, 'fabian', ?, ?, ?, ?, ?)
        """,
        (job.id, int(job.score or 0), _json(job.reasons), _json(job.risks), _recommendation(job), utc_now()),
    )


def _import_last_scan(conn: sqlite3.Connection, last_scan: dict[str, Any]) -> int | None:
    if not last_scan:
        return None
    cur = conn.execute(
        """
        INSERT INTO scans(started_at, finished_at, mode, scanned, skipped_login, added, updated, ignored_listing_pages, errors_json, summary_json)
        VALUES(?, ?, 'json_import', ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            last_scan.get("scanned_at"),
            last_scan.get("scanned_at"),
            int(last_scan.get("scanned") or 0),
            int(last_scan.get("skipped_login") or 0),
            int(last_scan.get("added") or 0),
            int(last_scan.get("updated") or 0),
            int(last_scan.get("ignored_listing_pages") or 0),
            _json(last_scan.get("errors") or []),
            _json({k: v for k, v in last_scan.items() if k != "events"}),
        ),
    )
    scan_id = int(cur.lastrowid)
    for event in last_scan.get("events") or []:
        meta = dict(event)
        status = meta.pop("status", "")
        stage = meta.pop("stage", "")
        message = meta.pop("message", "")
        source = meta.pop("source", "")
        url = meta.pop("url", "")
        conn.execute(
            """
            INSERT INTO scan_events(scan_id, status, stage, message, source_name, url, metadata_json, created_at)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (scan_id, status, stage, message, source, url, _json(meta), last_scan.get("scanned_at") or utc_now()),
        )
    return scan_id


def migrate_from_json(db_path: Path = DB_PATH, reset: bool = False) -> dict[str, Any]:
    if reset and db_path.exists():
        db_path.unlink()
    config = load_config()
    sources = _load_json(SOURCES_PATH, {"searches": [], "target_companies": [], "company_links": []})
    last_scan = _load_json(LAST_SCAN_PATH, {})
    jobs = load_jobs()
    with connect(db_path) as conn:
        init_db(conn)
        _upsert_candidate(conn, config.get("candidate", {}))
        for source in sources.get("searches", []):
            _upsert_source(conn, source)
        for link in sources.get("company_links", []):
            company = link.get("company")
            company_id = _upsert_company(conn, company)
            if company_id:
                conn.execute(
                    """
                    UPDATE companies
                    SET careers_url = COALESCE(NULLIF(?, ''), careers_url),
                        linkedin_url = COALESCE(NULLIF(?, ''), linkedin_url),
                        evidence_json = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        link.get("careers_search", ""),
                        link.get("linkedin_search", ""),
                        _json(link),
                        utc_now(),
                        company_id,
                    ),
                )
        for job in jobs:
            _upsert_job(conn, job)
        scan_id = _import_last_scan(conn, last_scan)
        conn.commit()
        return sqlite_report(conn) | {"db_path": str(db_path), "imported_scan_id": scan_id}


def sqlite_report(conn: sqlite3.Connection | None = None, db_path: Path = DB_PATH) -> dict[str, Any]:
    close = False
    if conn is None:
        conn = connect(db_path)
        close = True
    try:
        tables = ["candidates", "sources", "companies", "jobs", "raw_observations", "scans", "scan_events", "job_matches"]
        counts = {table: conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"] for table in tables}
        by_source_type = {row["source_type"]: row["n"] for row in conn.execute("SELECT source_type, COUNT(*) AS n FROM jobs GROUP BY source_type ORDER BY n DESC")}
        by_status = {row["status"]: row["n"] for row in conn.execute("SELECT status, COUNT(*) AS n FROM jobs GROUP BY status ORDER BY n DESC")}
        top_sources = [
            dict(row)
            for row in conn.execute(
                """
                SELECT s.name, s.source_type, COUNT(j.id) AS jobs, ROUND(AVG(j.score), 1) AS avg_score
                FROM sources s
                LEFT JOIN jobs j ON j.source_id = s.id
                GROUP BY s.id
                ORDER BY jobs DESC, s.name
                LIMIT 15
                """
            )
        ]
        quality = {
            "duplicate_canonical_urls": conn.execute(
                "SELECT COUNT(*) AS n FROM (SELECT canonical_url FROM jobs GROUP BY canonical_url HAVING COUNT(*) > 1)"
            ).fetchone()["n"],
            "listing_like_jobs": conn.execute(
                """
                SELECT COUNT(*) AS n FROM jobs
                WHERE company IN ('Get on Board', 'Trabajando')
                   OR lower(role) LIKE '%jobs | get on board%'
                   OR lower(role) LIKE '%portal de empleo%'
                """
            ).fetchone()["n"],
        }
        return {
            "db_path": str(db_path),
            "counts": counts,
            "by_source_type": by_source_type,
            "by_status": by_status,
            "top_sources": top_sources,
            "quality": quality,
        }
    finally:
        if close:
            conn.close()


def print_report(report: dict[str, Any]) -> None:
    print(json.dumps(report, ensure_ascii=False, indent=2))
