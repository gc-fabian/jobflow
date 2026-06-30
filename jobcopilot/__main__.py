from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
from datetime import datetime, timezone
from .storage import ROOT, CONFIG_PATH, DATA_PATH, load_config, save_config, load_jobs, save_jobs, next_id
from .models import Job
from .fetch import fetch_url_text
from .scoring import score_job
from .package import create_package


def cmd_init(args):
    if CONFIG_PATH.exists() and not args.force:
        print(f"Config ya existe: {CONFIG_PATH}")
        return
    example = ROOT / "config.example.json"
    config = json.loads(example.read_text(encoding="utf-8"))
    save_config(config)
    DATA_PATH.parent.mkdir(exist_ok=True)
    if not DATA_PATH.exists():
        save_jobs([])
    print(f"OK config: {CONFIG_PATH}")
    print(f"OK data: {DATA_PATH}")


def cmd_add_url(args):
    jobs = load_jobs()
    title, text = fetch_url_text(args.url)
    company = args.company or "[COMPLETAR EMPRESA]"
    role = args.role or (title if title else "[COMPLETAR CARGO]")
    job = Job(id=next_id(jobs), company=company, role=role, url=args.url, source=args.source, description=text)
    jobs.append(job)
    save_jobs(jobs)
    print(f"Agregada oferta #{job.id}: {job.company} — {job.role}")
    if text.startswith("[NO SE PUDO EXTRAER"):
        print(text)


def cmd_import_csv(args):
    jobs = load_jobs()
    with open(args.path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get("url") or row.get("link") or row.get("URL") or "[COMPLETAR URL]"
            company = row.get("company") or row.get("empresa") or row.get("Empresa") or "[COMPLETAR EMPRESA]"
            role = row.get("role") or row.get("cargo") or row.get("Cargo") or row.get("title") or "[COMPLETAR CARGO]"
            desc = row.get("description") or row.get("descripcion") or ""
            jobs.append(Job(id=next_id(jobs), company=company, role=role, url=url, source="csv", description=desc))
    save_jobs(jobs)
    print(f"Importadas ofertas. Total: {len(jobs)}")


def cmd_score(args):
    config = load_config()
    jobs = [score_job(j, config) for j in load_jobs()]
    for job in jobs:
        job.updated_at = datetime.now(timezone.utc).isoformat()
    save_jobs(jobs)
    print(f"Score actualizado para {len(jobs)} ofertas")


def cmd_list(args):
    jobs = sorted(load_jobs(), key=lambda j: j.score, reverse=True)
    if args.min_score is not None:
        jobs = [j for j in jobs if j.score >= args.min_score]
    for j in jobs[: args.limit]:
        print(f"#{j.id} [{j.score:>3}] {j.company} — {j.role} ({j.status})")
        print(f"    {j.url}")
        if args.reasons:
            for r in j.reasons[:5]:
                print(f"    - {r}")


def cmd_package(args):
    config = load_config()
    jobs = load_jobs()
    found = next((j for j in jobs if j.id == args.id), None)
    if not found:
        raise SystemExit(f"No existe oferta id {args.id}")
    if not found.score:
        found = score_job(found, config)
    folder = create_package(found, config, ROOT)
    found.status = "prepared"
    found.updated_at = datetime.now(timezone.utc).isoformat()
    save_jobs(jobs)
    print(f"Paquete creado: {folder}")




def cmd_db_init(args):
    from .sqlite_store import DB_PATH, connect, init_db, sqlite_report, print_report
    with connect(DB_PATH) as conn:
        init_db(conn)
        report = sqlite_report(conn, DB_PATH)
    print_report(report)


def cmd_db_migrate(args):
    from .sqlite_store import DB_PATH, migrate_from_json, print_report
    report = migrate_from_json(DB_PATH, reset=args.reset)
    print_report(report)


def cmd_db_report(args):
    from .sqlite_store import DB_PATH, print_report, sqlite_report
    if not DB_PATH.exists():
        raise SystemExit(f"No existe DB todavía: {DB_PATH}. Ejecuta: python -m jobcopilot db-migrate")
    print_report(sqlite_report(db_path=DB_PATH))


def cmd_scan(args):
    from .scanner import run_scan
    result = run_scan(limit_per_source=args.limit_per_source, include_login_required=args.include_login_required)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_research(args):
    from .research import run_research
    result = run_research(args.objective, mode=args.mode, user_id=args.user, max_pages=args.max_pages)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_serve(args):
    from .dashboard import serve
    serve(host=args.host, port=args.port, open_browser=not args.no_open)


def build_parser():
    p = argparse.ArgumentParser(prog="jobcopilot", description="Busca, filtra y prepara postulaciones human-in-the-loop")
    sub = p.add_subparsers(required=True)
    sp = sub.add_parser("init")
    sp.add_argument("--force", action="store_true")
    sp.set_defaults(func=cmd_init)

    sp = sub.add_parser("add-url")
    sp.add_argument("url")
    sp.add_argument("--company", default="")
    sp.add_argument("--role", default="")
    sp.add_argument("--source", default="manual")
    sp.set_defaults(func=cmd_add_url)

    sp = sub.add_parser("import-csv")
    sp.add_argument("path")
    sp.set_defaults(func=cmd_import_csv)

    sp = sub.add_parser("score")
    sp.set_defaults(func=cmd_score)

    sp = sub.add_parser("list")
    sp.add_argument("--limit", type=int, default=20)
    sp.add_argument("--min-score", type=int)
    sp.add_argument("--reasons", action="store_true")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("package")
    sp.add_argument("id", type=int)
    sp.set_defaults(func=cmd_package)

    sp = sub.add_parser("db-init", help="Crea la DB SQLite local normalizada sin importar datos")
    sp.set_defaults(func=cmd_db_init)

    sp = sub.add_parser("db-migrate", help="Importa JSON local a SQLite normalizado")
    sp.add_argument("--reset", action="store_true", help="Recrear data/jobflow.sqlite antes de importar")
    sp.set_defaults(func=cmd_db_migrate)

    sp = sub.add_parser("db-report", help="Muestra conteos/calidad de la DB SQLite")
    sp.set_defaults(func=cmd_db_report)

    sp = sub.add_parser("scan")
    sp.add_argument("--limit-per-source", type=int, default=8)
    sp.add_argument("--include-login-required", action="store_true", help="Solo marca/actualiza fuentes con login; no pide ni guarda claves")
    sp.set_defaults(func=cmd_scan)

    sp = sub.add_parser("research", help="Ejecuta investigación profunda/manual con presupuesto y fuentes públicas")
    sp.add_argument("objective", help="Objetivo de investigación, ej: backend fullstack remoto global")
    sp.add_argument("--mode", choices=["quick", "normal", "deep"], default="quick")
    sp.add_argument("--user", default="fabian")
    sp.add_argument("--max-pages", type=int, help="Sobrescribe el presupuesto máximo de páginas")
    sp.set_defaults(func=cmd_research)

    sp = sub.add_parser("serve")
    sp.add_argument("--host", default="127.0.0.1")
    sp.add_argument("--port", type=int, default=8765)
    sp.add_argument("--no-open", action="store_true")
    sp.set_defaults(func=cmd_serve)
    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
