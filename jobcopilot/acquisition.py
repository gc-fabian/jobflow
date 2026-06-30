from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from .models import Job


NORMALIZED_JOB_SCHEMA = {
    "id": "integer local, estable dentro del archivo local",
    "canonical_url": "URL normalizada usada para deduplicar",
    "source_name": "nombre de fuente configurada o entrada manual",
    "source_type": "public_listing | public_direct | manual_login | manual_entry | remote_board | company_careers | unknown",
    "channel": "portal normalizado: Get on Board, LinkedIn, AIRA, Trabajando, etc.",
    "company": "empresa normalizada si el extractor pudo inferirla",
    "role": "cargo/título normalizado",
    "location": "ubicación textual normalizada cuando está disponible",
    "description": "texto limpio o descripción extraída",
    "score": "calce contra perfil candidato",
    "status": "new | reviewed | prepared | sent | discarded | requires_info",
    "reasons": "razones explícitas del calce",
    "risks": "brechas/seniority/credenciales/datos faltantes",
    "created_at": "primera vez guardada",
    "updated_at": "última actualización local",
    "last_seen_at": "última vez vista en una fuente automática",
}


SOURCE_TYPE_RULES = {
    "linkedin": "manual_login",
    "getonboard": "public_listing",
    "get on board": "public_listing",
    "we work remotely": "remote_board",
    "weworkremotely": "remote_board",
    "remotive": "remote_board",
    "trabajando": "public_listing",
    "aira": "public_direct",
    "airavirtual": "public_direct",
    "manual": "manual_entry",
    "dashboard": "manual_entry",
}


def canonical_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url.strip())
    return parsed._replace(fragment="").geturl().rstrip("/").lower()


def classify_source(source: str, channel: str, url: str) -> str:
    text = f"{source} {channel} {url}".lower()
    for needle, source_type in SOURCE_TYPE_RULES.items():
        if needle in text:
            return source_type
    if url and url.startswith("http"):
        return "company_careers"
    return "unknown"


def normalized_job(job: Job) -> dict:
    return {
        "id": job.id,
        "canonical_url": canonical_url(job.url),
        "source_name": job.source or "unknown",
        "source_type": classify_source(job.source or "", job.channel or "", job.url or ""),
        "channel": job.channel,
        "company": job.company,
        "role": job.role,
        "location": job.location,
        "description_chars": len(job.description or ""),
        "score": job.score,
        "status": job.status,
        "reasons": job.reasons,
        "risks": job.risks,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "last_seen_at": job.last_seen_at,
        "url": job.url,
    }


def acquisition_report(jobs: list[Job], sources: dict, last_scan: dict, data_path: Path) -> dict:
    normalized = [normalized_job(job) for job in jobs]
    by_channel = Counter(item["channel"] or "sin canal" for item in normalized)
    by_source = Counter(item["source_name"] or "sin fuente" for item in normalized)
    by_source_type = Counter(item["source_type"] for item in normalized)
    by_status = Counter(item["status"] for item in normalized)
    duplicate_urls = [url for url, count in Counter(item["canonical_url"] for item in normalized if item["canonical_url"]).items() if count > 1]
    listing_like = [
        item for item in normalized
        if item["company"] in {"Get on Board", "Trabajando"}
        or "jobs | get on board" in item["role"].lower()
        or "portal de empleo" in item["role"].lower()
    ]
    missing_detail = [item for item in normalized if item["description_chars"] < 280]
    source_rows = []
    source_jobs: dict[str, list[dict]] = defaultdict(list)
    for item in normalized:
        source_jobs[item["source_name"]].append(item)
    configured = sources.get("searches", []) if isinstance(sources, dict) else []
    configured_by_name = {source.get("name", ""): source for source in configured if isinstance(source, dict)}
    for name, items in sorted(source_jobs.items(), key=lambda pair: len(pair[1]), reverse=True):
        configured_source = configured_by_name.get(name, {})
        source_rows.append({
            "name": name,
            "type": classify_source(name, items[0].get("channel", ""), configured_source.get("url") or items[0].get("url", "")),
            "configured": bool(configured_source),
            "configured_url": configured_source.get("url", ""),
            "login_required": bool(configured_source.get("login_required")),
            "jobs": len(items),
            "new": sum(1 for item in items if item["status"] == "new"),
            "prepared": sum(1 for item in items if item["status"] == "prepared"),
            "avg_score": round(sum(item["score"] for item in items) / max(1, len(items)), 1),
            "top_jobs": sorted(items, key=lambda item: item["score"], reverse=True)[:5],
        })
    for source in configured:
        name = source.get("name", "")
        if name and name not in source_jobs:
            source_rows.append({
                "name": name,
                "type": "manual_login" if source.get("login_required") else "configured_empty",
                "configured": True,
                "configured_url": source.get("url", ""),
                "login_required": bool(source.get("login_required")),
                "jobs": 0,
                "new": 0,
                "prepared": 0,
                "avg_score": 0,
                "top_jobs": [],
            })
    last_events = last_scan.get("events") or []
    sqlite_path = data_path.with_name("jobflow.sqlite")
    storage_note = (
        "SQLite local existe como espejo normalizado auto-sincronizado; JSON sigue siendo la fuente operativa actual."
        if sqlite_path.exists()
        else "Las ofertas reales se guardan localmente en data/jobs.json; no hay DB todavía."
    )
    sqlite_report_data = None
    if sqlite_path.exists():
        try:
            from .sqlite_store import sqlite_report
            sqlite_report_data = sqlite_report(db_path=sqlite_path)
        except Exception as exc:
            sqlite_report_data = {"error": str(exc)}
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "storage": {
            "kind": "local_json_with_sqlite_mirror" if sqlite_path.exists() else "local_json",
            "path": str(data_path),
            "size_bytes": data_path.stat().st_size if data_path.exists() else 0,
            "db": sqlite_path.exists(),
            "sqlite_path": str(sqlite_path) if sqlite_path.exists() else "",
            "sqlite_size_bytes": sqlite_path.stat().st_size if sqlite_path.exists() else 0,
            "note": storage_note,
        },
        "summary": {
            "jobs": len(jobs),
            "configured_sources": len(configured),
            "target_companies": len(sources.get("target_companies", [])) if isinstance(sources, dict) else 0,
            "company_links": len(sources.get("company_links", [])) if isinstance(sources, dict) else 0,
            "last_scan_at": last_scan.get("scanned_at"),
            "last_scan_added": last_scan.get("added", 0),
            "last_scan_updated": last_scan.get("updated", 0),
            "last_scan_events": len(last_events),
            "last_scan_errors": len(last_scan.get("errors") or []),
        },
        "counts": {
            "by_channel": dict(by_channel.most_common()),
            "by_source": dict(by_source.most_common()),
            "by_source_type": dict(by_source_type.most_common()),
            "by_status": dict(by_status.most_common()),
        },
        "sources": source_rows,
        "normalization": {
            "schema": NORMALIZED_JOB_SCHEMA,
            "current_state": "SQLite espejo normalizado auto-sincronizado" if sqlite_path.exists() else "parcialmente normalizado: Job tiene campos estándar, pero falta tabla/índice para fuentes, eventos e historial.",
            "recommended_next": "hacer que SQLite sea la fuente operativa principal del scanner/dashboard" if sqlite_path.exists() else "migrar a SQLite local con tablas jobs, sources, scans, scan_events y raw_observations.",
            "sqlite_report": sqlite_report_data,
        },
        "quality": {
            "duplicate_canonical_urls": len(duplicate_urls),
            "listing_like_jobs": len(listing_like),
            "missing_or_short_descriptions": len(missing_detail),
            "sample_listing_like_jobs": listing_like[:10],
            "sample_missing_detail_jobs": missing_detail[:10],
        },
        "automation": {
            "current": [
                "Escaneo manual desde botón o POST /api/scan.",
                "Auto-scan local opcional si config.automation.auto_scan_minutes > 0 al iniciar dashboard.",
                "Fuentes login_required se omiten automáticamente; LinkedIn queda manual por seguridad.",
            ],
            "recommended": [
                "Scheduler local para escanear fuentes públicas cada N horas.",
                "Persistir cada observación cruda antes de normalizar.",
                "Normalizar a tablas y deduplicar por URL + external_id + empresa/cargo.",
                "Mostrar una vista 'Adquisición' con fuente, método, última corrida, nuevas, actualizadas y errores.",
            ],
        },
    }
