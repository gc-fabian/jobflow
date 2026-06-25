from __future__ import annotations
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen

from .fetch import TextExtractor, fetch_url_text
from .models import Job, infer_channel
from .scoring import score_job
from .storage import ROOT, load_config, load_jobs, next_id, save_jobs

SOURCES_PATH = ROOT / "data" / "sources.json"
LAST_SCAN_PATH = ROOT / "data" / "last_scan.json"

ROLE_HINTS = (
    "software", "developer", "engineer", "backend", "fullstack", "full stack",
    "python", "node", "javascript", "typescript", "data", "devops", "product engineer",
    "desarrollador", "ingeniero", "programador",
)
JOB_URL_HINTS = (
    "/jobs/", "/empleos/programacion/", "/trabajo/", "/postula/", "/remote-jobs/", "greenhouse.io", "lever.co",
)
LISTING_URL_HINTS = (
    "linkedin.com/jobs/search", "/empleos/programacion", "/trabajo/tecnologia", "trabajando.cl/trabajo/", "remote-programming-jobs", "remote-jobs/software-dev",
)


@dataclass
class ScanResult:
    scanned: int = 0
    skipped_login: int = 0
    added: int = 0
    updated: int = 0
    ignored_listing_pages: int = 0
    errors: list[str] | None = None
    events: list[dict] | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["errors"] = data["errors"] or []
        data["events"] = data["events"] or []
        return data


def _event(result: ScanResult, status: str, stage: str, message: str, **data) -> None:
    """Append a human-readable trace entry for the dashboard debug view."""
    if result.events is None:
        result.events = []
    result.events.append({"status": status, "stage": stage, "message": message, **data})


def _search_plan(sources: dict) -> dict:
    searches = sources.get("searches", [])
    companies = sources.get("target_companies", [])
    return {
        "how_it_searches": [
            "1) Lee data/sources.json: búsquedas públicas, portales y empresas objetivo.",
            "2) Omite fuentes con login_required=true para no guardar claves ni romper términos de terceros.",
            "3) Descarga HTML público, busca JSON-LD JobPosting y links que parezcan ofertas reales.",
            "4) Filtra por keywords del perfil, roles preferidos y empresas objetivo.",
            "5) Deduplica por URL normalizada, puntúa cada oferta y guarda razones/riesgos.",
        ],
        "why_not_everything_appears": [
            "LinkedIn y algunos ATS ocultan datos si no hay sesión; se dejan como búsqueda manual.",
            "Páginas índice/listados genéricos no se guardan como oferta para no contaminar recomendaciones.",
            "Si una oferta no contiene keywords del perfil o parece senior/lead, puede quedar con score bajo o ser omitida.",
            "Algunos portales bloquean bots o entregan HTML incompleto; el debug muestra el motivo.",
        ],
        "configured_sources": len(searches),
        "login_required_sources": sum(1 for s in searches if s.get("login_required")),
        "public_sources": sum(1 for s in searches if not s.get("login_required")),
        "target_companies": companies,
    }


class LinkExtractor(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self._href: str | None = None
        self._text: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        attrs = dict(attrs)
        href = attrs.get("href")
        if href:
            self._href = urljoin(self.base_url, href)
            self._text = []

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href:
            text = " ".join(" ".join(self._text).split())
            if text:
                self.links.append((self._href, text))
            self._href = None
            self._text = []

    def handle_data(self, data):
        if self._href:
            self._text.append(data)


def _read_sources() -> dict:
    if not SOURCES_PATH.exists():
        return {"searches": [], "target_companies": []}
    return json.loads(SOURCES_PATH.read_text(encoding="utf-8"))


def _fetch_html(url: str, timeout: int = 20) -> tuple[str, str, str]:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 JobApplicationCopilot/0.2"})
    try:
        with urlopen(req, timeout=timeout) as res:
            raw = res.read(1_800_000)
            content_type = res.headers.get("content-type", "")
    except (HTTPError, URLError, TimeoutError) as exc:
        return "", "", f"[NO SE PUDO EXTRAER: {exc}]"
    encoding = "utf-8"
    if "charset=" in content_type:
        encoding = content_type.split("charset=", 1)[1].split(";", 1)[0].strip()
    html = raw.decode(encoding, errors="replace")
    parser = TextExtractor()
    parser.feed(html)
    text = chr(10).join(parser.parts)
    return parser.title.strip(), html, text[:12000]


def _is_relevant(text: str, config: dict, companies: list[str]) -> bool:
    lower = text.lower()
    keywords = [*config.get("must_have_keywords", []), *config.get("preferred_roles", []), *ROLE_HINTS]
    return any(k.lower() in lower for k in keywords) or any(c.lower() in lower for c in companies)


def _normalize_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url.strip())
    # Fragments like #! do not identify a separate job. Keep query because some ATS links need it.
    normalized = parsed._replace(fragment="")
    return urlunparse(normalized).rstrip("/").lower()


def _existing_by_url(jobs: list[Job]) -> dict[str, Job]:
    return {_normalize_url(j.url): j for j in jobs if j.url and not j.url.startswith("[COMPLETAR")}



def _company_from_role_title(role_text: str) -> str:
    pattern = r"\bat\s+(.+?)\s+-\s+(?:Chile|Remote|Remoto|Santiago|Argentina|Mexico|Colombia|Peru|Brasil|Brazil|South America)"
    match = re.search(pattern, role_text, re.I)
    if match:
        return match.group(1).strip()[:80]
    return ""


def _guess_company(source_name: str, role_text: str, companies: list[str]) -> str:
    from_title = _company_from_role_title(role_text)
    if from_title:
        return from_title
    text = f"{source_name} {role_text}".lower()
    for company in companies:
        if company.lower() in text:
            return company
    # GetOnBoard list labels often contain "Role Full time Company · Location".
    match = re.search(r"(?:full time|freelance|part time)\s+(.+?)\s+[·-]", role_text, re.I)
    if match:
        return match.group(1).strip()[:80]
    if " - " in source_name:
        return source_name.split(" - ", 1)[0].strip()
    return "[COMPLETAR EMPRESA]"

def _is_listing_page(url: str, source_name: str = "") -> bool:
    text = f"{url} {source_name}".lower()
    if "getonbrd.com/empleos/programacion" in text and text.rstrip("/").endswith("/empleos/programacion"):
        return True
    return any(hint in text for hint in LISTING_URL_HINTS) and "postula/" not in text


def _is_job_url(url: str) -> bool:
    lower = url.lower()
    if _is_listing_page(url):
        return False
    return any(hint in lower for hint in JOB_URL_HINTS)


def _jsonld_objects(html: str) -> list[dict]:
    objects: list[dict] = []
    pattern = r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>"
    for match in re.finditer(pattern, html, re.I | re.S):
        raw = unescape(match.group(1).strip())
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        items = parsed if isinstance(parsed, list) else [parsed]
        for item in items:
            if isinstance(item, dict):
                objects.append(item)
    return objects


def _jobposting_from_jsonld(html: str) -> dict | None:
    for obj in _jsonld_objects(html):
        if obj.get("@type") == "JobPosting":
            return obj
        graph = obj.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                if isinstance(item, dict) and item.get("@type") == "JobPosting":
                    return item
    return None


def _job_from_page(job_id: int, url: str, source_name: str, title: str, html: str, text: str, companies: list[str], now: str) -> Job:
    posting = _jobposting_from_jsonld(html) if html else None
    role = title or "[COMPLETAR CARGO]"
    company = _guess_company(source_name, role, companies)
    location = "Chile / remoto"
    description = text[:12000]
    if posting:
        role = posting.get("title") or role
        org = posting.get("hiringOrganization") or {}
        if isinstance(org, dict):
            company = org.get("name") or company
        desc = posting.get("description")
        if desc:
            description = re.sub("<[^>]+>", " ", desc)
            description = " ".join(unescape(description).split())[:12000]
    title_company = _company_from_role_title(role)
    if title_company:
        company = title_company
    if posting:
        location_data = posting.get("jobLocation")
        if isinstance(location_data, dict):
            address = location_data.get("address") or {}
            if isinstance(address, dict):
                parts = [address.get("addressLocality"), address.get("addressRegion"), address.get("addressCountry")]
                location = ", ".join(p for p in parts if p) or location
    return Job(
        id=job_id,
        company=company,
        role=role[:160],
        url=url,
        source=source_name,
        location=location,
        description=description,
        status="new",
        last_seen_at=now,
        channel=infer_channel(url, source_name),
    )


def run_scan(limit_per_source: int = 8, include_login_required: bool = False) -> dict:
    config = load_config()
    sources = _read_sources()
    companies = sources.get("target_companies", [])
    jobs = load_jobs()
    by_url = _existing_by_url(jobs)
    now = datetime.now(timezone.utc).isoformat()
    result = ScanResult(errors=[], events=[])

    _event(result, "info", "plan", "Plan de búsqueda cargado", **_search_plan(sources))

    for source in sources.get("searches", []):
        name = source.get("name", "fuente")
        url = source.get("url", "")
        if not url:
            _event(result, "skip", "source", "Fuente sin URL; se omite", source=name)
            continue
        if source.get("login_required") and not include_login_required:
            result.skipped_login += 1
            _event(
                result,
                "skip",
                "source",
                "Omitida porque requiere login manual; se evita guardar credenciales o automatizar sesiones privadas.",
                source=name,
                url=url,
            )
            continue

        result.scanned += 1
        _event(result, "start", "fetch", "Descargando fuente pública", source=name, url=url)
        title, html, text = _fetch_html(url, timeout=15)
        if text.startswith("[NO SE PUDO EXTRAER"):
            result.errors.append(f"{name}: {text}")
            _event(result, "error", "fetch", "No se pudo extraer HTML/texto de la fuente", source=name, url=url, error=text)
            continue
        _event(
            result,
            "ok",
            "fetch",
            "Fuente descargada; se revisa si es oferta directa o listado.",
            source=name,
            url=url,
            title=title,
            text_chars=len(text),
            html_chars=len(html),
        )

        listing_page = _is_listing_page(url, name)
        posting = _jobposting_from_jsonld(html)
        relevant_source = _is_relevant(" ".join([name, title, text[:3000]]), config, companies)
        if posting or (not listing_page and relevant_source):
            key = _normalize_url(url)
            reason = "JSON-LD JobPosting detectado" if posting else "fuente no-listado con keywords/empresa relevante"
            if key in by_url:
                by_url[key].last_seen_at = now
                by_url[key].updated_at = now
                by_url[key] = score_job(by_url[key], config)
                result.updated += 1
                _event(result, "update", "job", "Oferta directa existente actualizada", source=name, url=url, reason=reason, job_id=by_url[key].id)
            else:
                job = _job_from_page(next_id(jobs), url, name, title, html, text, companies, now)
                scored = score_job(job, config)
                jobs.append(scored)
                by_url[key] = scored
                result.added += 1
                _event(result, "add", "job", "Oferta directa agregada", source=name, url=url, reason=reason, job_id=scored.id, company=scored.company, role=scored.role, score=scored.score)
        elif listing_page:
            result.ignored_listing_pages += 1
            _event(result, "info", "listing", "Página de listado detectada; no se guarda como oferta, se extraen links internos.", source=name, url=url)
        else:
            _event(result, "skip", "source", "Fuente pública descargada pero no parece oferta ni contiene suficientes keywords del perfil.", source=name, url=url, title=title)

        extractor = LinkExtractor(url)
        try:
            extractor.feed(html)
        except Exception as exc:
            result.errors.append(f"{name}: error leyendo links: {exc}")
            _event(result, "error", "links", "Error leyendo links del HTML", source=name, url=url, error=str(exc))
            continue
        _event(result, "info", "links", "Links encontrados en la fuente", source=name, total_links=len(extractor.links), limit_per_source=limit_per_source)

        added_from_source = 0
        seen_links: set[str] = set()
        skipped_non_job = 0
        skipped_not_relevant = 0
        skipped_duplicate = 0
        for link, label in extractor.links:
            if added_from_source >= limit_per_source:
                _event(result, "info", "limit", "Se alcanzó el límite por fuente para evitar ruido/spam.", source=name, limit_per_source=limit_per_source)
                break
            key = _normalize_url(link)
            if key in seen_links:
                skipped_duplicate += 1
                continue
            if not _is_job_url(link):
                skipped_non_job += 1
                continue
            seen_links.add(key)
            if not _is_relevant(label, config, companies):
                skipped_not_relevant += 1
                _event(result, "skip", "candidate", "Link parece oferta, pero el texto del link no calza con keywords/empresas objetivo.", source=name, url=link, label=label[:180])
                continue
            if key in by_url:
                by_url[key].last_seen_at = now
                by_url[key].updated_at = now
                if by_url[key].company in {"Get on Board", "Trabajando", "[COMPLETAR EMPRESA]"}:
                    by_url[key].company = _guess_company(name, label, companies)
                by_url[key] = score_job(by_url[key], config)
                result.updated += 1
                _event(result, "update", "candidate", "Oferta existente vista de nuevo y actualizada", source=name, url=link, label=label[:180], job_id=by_url[key].id, score=by_url[key].score)
                continue
            _event(result, "start", "detail", "Link candidato relevante; descargando detalle", source=name, url=link, label=label[:180])
            detail_title, detail_html, detail_text = _fetch_html(link, timeout=12)
            if detail_text.startswith("[NO SE PUDO EXTRAER"):
                _event(result, "error", "detail", "No se pudo abrir detalle de oferta", source=name, url=link, error=detail_text)
                continue
            label_text = " ".join([label, detail_title, detail_text[:2000]])
            if not _is_relevant(label_text, config, companies):
                skipped_not_relevant += 1
                _event(result, "skip", "detail", "Detalle descargado, pero no conserva señales suficientes de calce.", source=name, url=link, title=detail_title, label=label[:180])
                continue
            job = _job_from_page(next_id(jobs), link, name, detail_title or label, detail_html, detail_text or label, companies, now)
            if job.company == "[COMPLETAR EMPRESA]":
                job.company = _guess_company(name, label, companies)
            scored = score_job(job, config)
            jobs.append(scored)
            by_url[key] = scored
            result.added += 1
            added_from_source += 1
            _event(result, "add", "candidate", "Oferta agregada desde link interno", source=name, url=link, label=label[:180], job_id=scored.id, company=scored.company, role=scored.role, score=scored.score, reasons=scored.reasons[:5], risks=scored.risks[:5])
        _event(result, "info", "summary", "Resumen de links omitidos en esta fuente", source=name, skipped_non_job=skipped_non_job, skipped_duplicate=skipped_duplicate, skipped_not_relevant=skipped_not_relevant, added_from_source=added_from_source)

    save_jobs(jobs)
    payload = {"scanned_at": now, **result.to_dict(), "search_plan": _search_plan(sources)}
    LAST_SCAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    LAST_SCAN_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def load_last_scan() -> dict:
    if not LAST_SCAN_PATH.exists():
        return {}
    return json.loads(LAST_SCAN_PATH.read_text(encoding="utf-8"))
