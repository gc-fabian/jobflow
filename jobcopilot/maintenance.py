from __future__ import annotations

from urllib.parse import urlparse

from .models import Job
from .scanner import _is_listing_page


def is_listing_like_job(job: Job) -> bool:
    url = job.url or ""
    role = (job.role or "").lower()
    company = (job.company or "").lower()
    parsed = urlparse(url)
    path = parsed.path.rstrip("/").lower()
    if _is_listing_page(url, job.source):
        return True
    if company in {"get on board", "trabajando"}:
        return True
    if "jobs | get on board" in role or "portal de empleo" in role:
        return True
    if "getonbrd.com" in parsed.netloc.lower() and not any(part in path for part in ["/jobs/programming/", "/jobs/programacion/"]):
        return True
    return False


def remove_listing_like_jobs(jobs: list[Job]) -> tuple[list[Job], list[Job]]:
    removed = [job for job in jobs if is_listing_like_job(job)]
    kept = [job for job in jobs if not is_listing_like_job(job)]
    return kept, removed
