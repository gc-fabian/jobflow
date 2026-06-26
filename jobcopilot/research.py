from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote_plus, urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from .models import Job, infer_channel
from .scoring import score_job
from .storage import ROOT, load_config, load_jobs, next_id, save_jobs
from .scanner import LinkExtractor, _fetch_html, _is_job_url, _job_from_page, _normalize_url, _search_plan

RESEARCH_ROOT = ROOT / "exports" / "research_runs"
RARE_SOURCE_TEMPLATES = [
    {
        "name": "GetOnBoard global query",
        "url": "https://www.getonbrd.com/empleos/programacion?query={query}",
        "kind": "job_board",
        "country": "LatAm/remote",
    },
    {
        "name": "We Work Remotely programming",
        "url": "https://weworkremotely.com/categories/remote-programming-jobs",
        "kind": "remote_board",
        "country": "global",
    },
    {
        "name": "Hacker News Who is Hiring",
        "url": "https://www.ycombinator.com/companies/jobs?role=eng",
        "kind": "startup_board",
        "country": "global",
    },
    {
        "name": "YC Work at a Startup engineering",
        "url": "https://www.ycombinator.com/companies/jobs?role=eng&remote=Remote",
        "kind": "startup_board",
        "country": "global_remote",
    },
    {
        "name": "Wellfound startups search",
        "url": "https://wellfound.com/jobs?query={query}",
        "kind": "startup_board",
        "country": "global",
    },
    {
        "name": "Google manual careers search",
        "url": "https://www.google.com/search?q={query}%20careers%20remote%20software%20engineer",
        "kind": "manual_search",
        "country": "global",
        "manual_only": True,
    },
]


@dataclass
class ResearchBudget:
    max_queries: int = 8
    max_sources: int = 12
    max_pages: int = 45
    max_links_per_source: int = 8


@dataclass
class ResearchPage:
    url: str
    title: str = ""
    page_type: str = "unknown"
    status: str = "pending"
    source: str = ""
    snippet: str = ""
    reason: str = ""


@dataclass
class ResearchRun:
    id: str
    objective: str
    mode: str
    user_id: str = "default"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    budget: dict = field(default_factory=dict)
    queries: list[str] = field(default_factory=list)
    pages: list[ResearchPage] = field(default_factory=list)
    jobs_added: int = 0
    jobs_updated: int = 0
    companies: list[str] = field(default_factory=list)
    market_signals: dict[str, int] = field(default_factory=dict)
    skipped: list[dict] = field(default_factory=list)


def _slug(text: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ]+", "_", text.strip().lower()).strip("_")
    return clean[:72] or "research"


def _as_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def generate_queries(config: dict, objective: str, limit: int = 8) -> list[str]:
    candidate = config.get("candidate", {})
    roles = _as_list(candidate.get("target_roles")) or _as_list(config.get("preferred_roles"))
    skills = (_as_list(candidate.get("skills_core")) + _as_list(candidate.get("skills_plus")))[:10]
    locations = _as_list(candidate.get("locations")) or ["Chile", "remote LatAm", "global remote"]
    base_terms = []
    for role in roles[:5]:
        for loc in locations[:3]:
            tech = " ".join(skills[:4])
            base_terms.append(f"{role} {tech} {loc}")
    objective_terms = objective.strip()
    if objective_terms:
        base_terms.insert(0, objective_terms)
    # Add rare/global variants.
    base_terms.extend([
        "backend developer node typescript remote latam",
        "full stack developer react node remote global",
        "software engineer python postgres remote startup",
        "product engineer automation ai remote",
    ])
    seen = []
    for q in base_terms:
        q = " ".join(q.split())
        if q.lower() not in [x.lower() for x in seen]:
            seen.append(q)
    return seen[:limit]


def build_research_sources(config: dict, objective: str, budget: ResearchBudget) -> tuple[list[str], list[dict]]:
    queries = generate_queries(config, objective, budget.max_queries)
    sources: list[dict] = []
    for query in queries:
        for template in RARE_SOURCE_TEMPLATES:
            url = template["url"].format(query=quote_plus(query))
            source = dict(template)
            source["query"] = query
            source["url"] = url
            source["name"] = f"{template['name']} — {query[:54]}"
            sources.append(source)
    # Add company career searches as manual evidence targets.
    companies = config.get("target_companies", [])
    # Current app stores companies in sources.json, not config; keep this hook for future multi-user profiles.
    deduped = []
    seen = set()
    for source in sources:
        key = source["url"].lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(source)
        if len(deduped) >= budget.max_sources:
            break
    return queries, deduped


def classify_page(url: str, title: str, text: str) -> tuple[str, str]:
    low = " ".join([url, title, text[:3000]]).lower()
    if any(x in low for x in ["login", "sign in", "captcha", "access denied", "forbidden"]):
        return "blocked_or_login", "login/captcha/bloqueo visible"
    if any(x in low for x in ["jobposting", "apply", "postula", "responsibilities", "requirements", "requisitos", "remote", "engineer"]):
        if _is_job_url(url) or any(x in low for x in ["requirements", "requisitos", "responsibilities", "apply"]):
            return "job_or_job_list", "señales de oferta/listado"
    if any(x in low for x in ["careers", "trabaja con nosotros", "jobs", "hiring"]):
        return "career_page", "página de carreras/listado"
    if any(x in low for x in ["engineering blog", "tech blog", "github", "stack"]):
        return "company_signal", "señal técnica/empresa"
    return "unknown", "sin señales fuertes"


def market_signals_from_text(text: str) -> dict[str, int]:
    terms = [
        "node", "node.js", "typescript", "javascript", "react", "python", "sql", "postgres", "mongodb",
        "aws", "gcp", "azure", "docker", "kubernetes", "remote", "latam", "english", "inglés",
        "senior", "junior", "backend", "full stack", "frontend", "api", "microservices",
    ]
    low = text.lower()
    return {term: low.count(term) for term in terms if low.count(term) > 0}



def _is_bad_research_link(url: str, label: str = "") -> bool:
    text = f"{url} {label}".lower()
    blocked = [
        "post-a-job", "post a job", "find-your-plan", "pricing", "utm_content=post-job",
        "login", "sign-in", "signup", "register", "newsletter", "terms", "privacy",
    ]
    return any(term in text for term in blocked)


def _merge_counts(total: dict[str, int], part: dict[str, int]) -> None:
    for key, value in part.items():
        total[key] = total.get(key, 0) + value


def _run_dir(run_id: str) -> Path:
    return RESEARCH_ROOT / run_id


def _write_report(run: ResearchRun, run_dir: Path) -> None:
    opportunities = [p for p in run.pages if p.page_type in {"job_or_job_list", "career_page"} and p.status == "ok"]
    blocked = [p for p in run.pages if p.page_type == "blocked_or_login" or p.status != "ok"]
    signals = sorted(run.market_signals.items(), key=lambda kv: kv[1], reverse=True)[:20]
    lines = [
        f"# Research run — {run.objective}",
        "",
        f"ID: `{run.id}`",
        f"Usuario: `{run.user_id}`",
        f"Modo: `{run.mode}`",
        f"Fecha: {run.created_at}",
        "",
        "## Presupuesto",
        "",
        "```json",
        json.dumps(run.budget, ensure_ascii=False, indent=2),
        "```",
        "",
        "## Queries generadas",
        "",
    ]
    lines.extend(f"- {q}" for q in run.queries)
    lines += ["", "## Mejores hallazgos / oportunidades", ""]
    if opportunities:
        for page in opportunities[:30]:
            lines.append(f"- **{page.title or page.source}** — {page.page_type}")
            lines.append(f"  - URL: {page.url}")
            lines.append(f"  - Fuente: {page.source}")
            lines.append(f"  - Motivo: {page.reason}")
            if page.snippet:
                lines.append(f"  - Snippet: {page.snippet[:260]}")
    else:
        lines.append("- No se detectaron oportunidades fuertes en este run. Aumentar presupuesto o agregar fuentes.")
    lines += ["", "## Señales de mercado", ""]
    if signals:
        lines.extend(f"- {k}: {v}" for k, v in signals)
    else:
        lines.append("- Sin señales suficientes.")
    lines += ["", "## Bloqueos / fuentes manuales", ""]
    if blocked:
        for page in blocked[:25]:
            lines.append(f"- {page.source}: {page.status} / {page.page_type} — {page.url}")
    else:
        lines.append("- Sin bloqueos importantes.")
    lines += [
        "",
        "## Recomendación",
        "",
        "- Convertir hallazgos buenos en ofertas guardadas y revisar score/cv antes de postular.",
        "- Usar fuentes manuales con login solo desde navegador del usuario; no guardar credenciales.",
        "- Para investigación de postulantes/trabajadores, guardar señales agregadas de skills/seniority, no datos personales innecesarios.",
    ]
    (run_dir / "research_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_research(objective: str, mode: str = "quick", user_id: str = "default", max_pages: int | None = None) -> dict:
    config = load_config()
    if mode == "deep":
        budget = ResearchBudget(max_queries=12, max_sources=24, max_pages=160, max_links_per_source=12)
    elif mode == "normal":
        budget = ResearchBudget(max_queries=8, max_sources=14, max_pages=80, max_links_per_source=8)
    else:
        budget = ResearchBudget(max_queries=5, max_sources=8, max_pages=30, max_links_per_source=5)
    if max_pages is not None:
        budget.max_pages = max_pages

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + _slug(objective)
    run = ResearchRun(id=run_id, objective=objective, mode=mode, user_id=user_id, budget=asdict(budget))
    queries, sources = build_research_sources(config, objective, budget)
    run.queries = queries
    run_dir = _run_dir(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    jobs = load_jobs()
    by_url = {_normalize_url(j.url): j for j in jobs if j.url}
    pages_seen: set[str] = set()
    pages_fetched = 0
    now = datetime.now(timezone.utc).isoformat()
    companies: set[str] = set()

    for source in sources:
        if pages_fetched >= budget.max_pages:
            break
        if source.get("manual_only"):
            run.pages.append(ResearchPage(url=source["url"], title=source["name"], page_type="manual_search", status="manual_only", source=source["name"], reason="fuente útil pero manual/externa"))
            continue
        url = source["url"]
        key = _normalize_url(url)
        if key in pages_seen:
            continue
        pages_seen.add(key)
        title, html, text = _fetch_html(url, timeout=15)
        pages_fetched += 1
        if text.startswith("[NO SE PUDO EXTRAER"):
            run.pages.append(ResearchPage(url=url, title=title, page_type="error", status="error", source=source["name"], reason=text))
            continue
        page_type, reason = classify_page(url, title, text)
        run.pages.append(ResearchPage(url=url, title=title, page_type=page_type, status="ok", source=source["name"], snippet=" ".join(text.split())[:500], reason=reason))
        _merge_counts(run.market_signals, market_signals_from_text(text))

        extractor = LinkExtractor(url)
        try:
            extractor.feed(html)
        except Exception:
            continue
        added_links = 0
        for link, label in extractor.links:
            if pages_fetched >= budget.max_pages or added_links >= budget.max_links_per_source:
                break
            if _is_bad_research_link(link, label) or not _is_job_url(link):
                continue
            link_key = _normalize_url(link)
            if link_key in pages_seen:
                continue
            pages_seen.add(link_key)
            dtitle, dhtml, dtext = _fetch_html(link, timeout=12)
            pages_fetched += 1
            if dtext.startswith("[NO SE PUDO EXTRAER"):
                run.pages.append(ResearchPage(url=link, title=label[:160], page_type="error", status="error", source=source["name"], reason=dtext))
                continue
            dtype, dreason = classify_page(link, dtitle or label, dtext)
            run.pages.append(ResearchPage(url=link, title=dtitle or label, page_type=dtype, status="ok", source=source["name"], snippet=" ".join(dtext.split())[:500], reason=dreason))
            _merge_counts(run.market_signals, market_signals_from_text(" ".join([label, dtitle, dtext[:3000]])))
            if dtype in {"job_or_job_list", "career_page"} and link_key not in by_url:
                job = _job_from_page(next_id(jobs), link, source["name"], dtitle or label, dhtml, dtext or label, [], now)
                scored = score_job(job, config)
                jobs.append(scored)
                by_url[link_key] = scored
                run.jobs_added += 1
                added_links += 1
                if scored.company and not scored.company.startswith("["):
                    companies.add(scored.company)
            elif link_key in by_url:
                by_url[link_key].last_seen_at = now
                by_url[link_key].updated_at = now
                by_url[link_key] = score_job(by_url[link_key], config)
                run.jobs_updated += 1
                added_links += 1

    run.companies = sorted(companies)
    save_jobs(jobs)
    (run_dir / "research_run.json").write_text(json.dumps(asdict(run), ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "opportunities.json").write_text(json.dumps([j.to_dict() for j in sorted(jobs, key=lambda x: x.score, reverse=True)[:50]], ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "market_signals.json").write_text(json.dumps(run.market_signals, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_report(run, run_dir)
    return {"ok": True, "run_id": run.id, "folder": str(run_dir), "jobs_added": run.jobs_added, "jobs_updated": run.jobs_updated, "pages": len(run.pages), "report": str(run_dir / "research_report.md")}
