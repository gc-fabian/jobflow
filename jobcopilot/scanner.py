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
    "/jobs/", "/empleos/programacion/", "/trabajo/", "/postula/", "greenhouse.io", "lever.co",
)
LISTING_URL_HINTS = (
    "linkedin.com/jobs/search", "/empleos/programacion", "/trabajo/tecnologia", "trabajando.cl/trabajo/",
)


@dataclass
class ScanResult:
    scanned: int = 0
    skipped_login: int = 0
    added: int = 0
    updated: int = 0
    ignored_listing_pages: int = 0
    errors: list[str] | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["errors"] = data["errors"] or []
        return data


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
    result = ScanResult(errors=[])

    for source in sources.get("searches", []):
        name = source.get("name", "fuente")
        url = source.get("url", "")
        if not url:
            continue
        if source.get("login_required") and not include_login_required:
            result.skipped_login += 1
            continue
        result.scanned += 1
        title, html, text = _fetch_html(url, timeout=15)
        if text.startswith("[NO SE PUDO EXTRAER"):
            result.errors.append(f"{name}: {text}")
            continue

        listing_page = _is_listing_page(url, name)
        posting = _jobposting_from_jsonld(html)
        if posting or (not listing_page and _is_relevant(" ".join([name, title, text[:3000]]), config, companies)):
            key = _normalize_url(url)
            if key in by_url:
                by_url[key].last_seen_at = now
                by_url[key].updated_at = now
                by_url[key] = score_job(by_url[key], config)
                result.updated += 1
            else:
                job = _job_from_page(next_id(jobs), url, name, title, html, text, companies, now)
                jobs.append(score_job(job, config))
                by_url[key] = job
                result.added += 1
        elif listing_page:
            result.ignored_listing_pages += 1

        extractor = LinkExtractor(url)
        try:
            extractor.feed(html)
        except Exception as exc:
            result.errors.append(f"{name}: error leyendo links: {exc}")
            continue
        added_from_source = 0
        seen_links: set[str] = set()
        for link, label in extractor.links:
            if added_from_source >= limit_per_source:
                break
            key = _normalize_url(link)
            if key in seen_links or not _is_job_url(link):
                continue
            seen_links.add(key)
            if not _is_relevant(label, config, companies):
                continue
            if key in by_url:
                by_url[key].last_seen_at = now
                by_url[key].updated_at = now
                if by_url[key].company in {"Get on Board", "Trabajando", "[COMPLETAR EMPRESA]"}:
                    by_url[key].company = _guess_company(name, label, companies)
                by_url[key] = score_job(by_url[key], config)
                result.updated += 1
                continue
            detail_title, detail_html, detail_text = _fetch_html(link, timeout=12)
            label_text = " ".join([label, detail_title, detail_text[:2000]])
            if not _is_relevant(label_text, config, companies):
                continue
            job = _job_from_page(next_id(jobs), link, name, detail_title or label, detail_html, detail_text or label, companies, now)
            if job.company == "[COMPLETAR EMPRESA]":
                job.company = _guess_company(name, label, companies)
            jobs.append(score_job(job, config))
            by_url[key] = job
            result.added += 1
            added_from_source += 1

    save_jobs(jobs)
    payload = {"scanned_at": now, **result.to_dict()}
    LAST_SCAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    LAST_SCAN_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def load_last_scan() -> dict:
    if not LAST_SCAN_PATH.exists():
        return {}
    return json.loads(LAST_SCAN_PATH.read_text(encoding="utf-8"))
