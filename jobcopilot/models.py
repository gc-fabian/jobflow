from __future__ import annotations
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any
from .text_cleaning import clean_job_description


@dataclass
class Job:
    id: int
    company: str
    role: str
    url: str
    source: str = "manual"
    location: str = "[COMPLETAR]"
    description: str = ""
    status: str = "new"
    score: int = 0
    reasons: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    channel: str = "[COMPLETAR CANAL]"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_seen_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Job":
        data = dict(data)
        data.setdefault("reasons", [])
        data.setdefault("risks", [])
        data.setdefault("channel", infer_channel(data.get("url", ""), data.get("source", "")))
        data.setdefault("last_seen_at", "")
        data["description"] = clean_job_description(data.get("description", ""))
        if data.get("status") == "found":
            data["status"] = "new"
        return cls(**data)


def infer_channel(url: str, source: str = "") -> str:
    text = f"{url} {source}".lower()
    if "linkedin.com" in text:
        return "LinkedIn (login manual)"
    if "airavirtual" in text or "aira" in text:
        return "AIRA"
    if "getonbrd" in text or "get on board" in text:
        return "Get on Board"
    if "trabajando" in text:
        return "Trabajando"
    if "lever.co" in text:
        return "Lever"
    if "greenhouse" in text:
        return "Greenhouse"
    if "buk.cl" in text or "buk" in text:
        return "Buk / portal empresa"
    if "mailto:" in text:
        return "Email"
    if url:
        return "Portal empresa / web"
    return "[COMPLETAR CANAL]"
