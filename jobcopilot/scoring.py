from __future__ import annotations
from .models import Job, infer_channel


EXPERIENCE_RISK_TERMS = [
    "senior", "lead", "principal", "staff", "head", "manager",
    "5 años", "5+ años", "6 años", "7 años", "8 años", "10 años",
]
MISSING_DETAIL_TERMS = ["[completar", "sin descripción", "no se pudo extraer"]
CLOUD_TERMS = ["aws", "gcp", "azure", "cloud"]


def _as_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip()]
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def score_job(job: Job, config: dict) -> Job:
    candidate = config.get("candidate", {})
    text = " ".join([job.company, job.role, job.location, job.description]).lower()
    score = 0
    reasons: list[str] = []
    risks: list[str] = []

    must_keywords = list(config.get("must_have_keywords", []))
    for field in ("skills_core", "skills_plus"):
        for kw in _as_list(candidate.get(field)):
            if kw.lower() not in [x.lower() for x in must_keywords]:
                must_keywords.append(kw)
    preferred_roles = list(config.get("preferred_roles", []))
    for role in _as_list(candidate.get("target_roles")):
        if role.lower() not in [x.lower() for x in preferred_roles]:
            preferred_roles.append(role)
    avoid_keywords = list(config.get("avoid_keywords", []))
    for bad in _as_list(candidate.get("deal_breakers")):
        if bad.lower() not in [x.lower() for x in avoid_keywords]:
            avoid_keywords.append(bad)

    for kw in must_keywords:
        if kw.lower() in text:
            score += 8
            reasons.append(f"+ keyword: {kw}")

    for role in preferred_roles:
        if role.lower() in text:
            score += 15
            reasons.append(f"+ rol preferido: {role}")

    for bad in avoid_keywords:
        if bad.lower() in text:
            score -= 20
            risks.append(f"posible descarte/stretch: {bad}")

    if "junior" in text or "0-2" in text or "1-2" in text or "trainee" in text:
        score += 12
        reasons.append("+ seniority razonable")
    if "senior" in text and "junior" not in text:
        score -= 18
        risks.append("seniority alto / stretch")
    if "remoto" in text or "remote" in text or "híbr" in text or "hybrid" in text:
        score += 5
        reasons.append("+ modalidad flexible")

    for mode in _as_list(candidate.get("preferred_work_modes")):
        if mode.lower() in text:
            score += 4
            reasons.append(f"+ preferencia usuario: {mode}")
    for location in _as_list(candidate.get("locations")):
        if location.lower() in text:
            score += 3
            reasons.append(f"+ ubicación objetivo: {location}")
    if candidate.get("seniority_target") and any(term in text for term in ["junior", "trainee", "semi senior", "semi-senior", "0-2", "1-2", "0 a 3"]):
        score += 8
        reasons.append("+ seniority dentro del objetivo del usuario")

    if not any(term in text for term in CLOUD_TERMS):
        risks.append("cloud/infra no visible en la oferta o requiere validación")
    if any(term in text for term in EXPERIENCE_RISK_TERMS):
        risks.append("revisar años/seniority antes de postular")
    if not job.description.strip() or any(term in text for term in MISSING_DETAIL_TERMS):
        risks.append("falta descripción completa; pegar texto desde portal/logged-in")
    if "certificacion" in text or "certificación" in text:
        risks.append("menciona certificación; no inventar, dejar como brecha si es requisito")

    job.score = max(-100, min(100, score))
    job.reasons = reasons[:12]
    # Preserve order while deduplicating.
    job.risks = list(dict.fromkeys(risks))[:8]
    job.channel = infer_channel(job.url, job.source)
    return job
