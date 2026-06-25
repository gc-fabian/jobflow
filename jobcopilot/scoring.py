from __future__ import annotations
from .models import Job, infer_channel


EXPERIENCE_RISK_TERMS = [
    "senior", "lead", "principal", "staff", "head", "manager",
    "5 años", "5+ años", "6 años", "7 años", "8 años", "10 años",
]
MISSING_DETAIL_TERMS = ["[completar", "sin descripción", "no se pudo extraer"]
CLOUD_TERMS = ["aws", "gcp", "azure", "cloud"]


def score_job(job: Job, config: dict) -> Job:
    text = " ".join([job.company, job.role, job.location, job.description]).lower()
    score = 0
    reasons: list[str] = []
    risks: list[str] = []

    for kw in config.get("must_have_keywords", []):
        if kw.lower() in text:
            score += 8
            reasons.append(f"+ keyword: {kw}")

    for role in config.get("preferred_roles", []):
        if role.lower() in text:
            score += 15
            reasons.append(f"+ rol preferido: {role}")

    for bad in config.get("avoid_keywords", []):
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
