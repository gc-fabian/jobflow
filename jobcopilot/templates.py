from __future__ import annotations
from .models import Job


def _join(items, fallback="[COMPLETAR]") -> str:
    if isinstance(items, list):
        clean = [str(x) for x in items if str(x).strip()]
        return ", ".join(clean) if clean else fallback
    if isinstance(items, str) and items.strip():
        return items
    return fallback


def email_subject(job: Job) -> str:
    return f"Postulación {job.role} – Fabián Godoy"


def application_email(job: Job, config: dict) -> str:
    c = config["candidate"]
    headline = c.get("headline") or c.get("base_profile") or "Software Engineer / Backend / Fullstack"
    skills = _join(c.get("skills_core"), "Node.js, Python, APIs, bases de datos y automatización")
    strengths = _join(c.get("skills_plus"), "IA aplicada, integración de sistemas y aprendizaje rápido")
    return f"""Estimados/as,

Junto con saludar, les envío mi postulación para el cargo de {job.role} en {job.company}.

Soy {headline}. Mi foco principal está en {skills}, con fortalezas adicionales en {strengths}. Me interesa esta oportunidad porque calza con mi búsqueda actual y con el tipo de problemas donde puedo aportar con criterio técnico, ejecución y aprendizaje rápido.

Adjunto mi CV y quedo disponible para conversar.

Saludos cordiales,
{c.get('name', '[COMPLETAR NOMBRE]')}
{c.get('email', '[COMPLETAR EMAIL]')}
{c.get('phone', '[COMPLETAR TELÉFONO]')}
GitHub: {c.get('github', '[COMPLETAR GITHUB]')}
LinkedIn: {c.get('linkedin', '[COMPLETAR LINKEDIN]')}
"""


def form_text(job: Job, config: dict) -> str:
    c = config["candidate"]
    headline = c.get("headline") or "Software Engineer / Backend / Fullstack"
    skills = _join(c.get("skills_core"), "Node.js, Python, APIs, bases de datos y automatización")
    projects = _join(c.get("evidence_projects"), "proyectos de software end-to-end e IA aplicada")
    voice = c.get("application_voice", "Profesional, honesto y breve; no exagerar seniority.")
    return f"""Soy {headline}, con foco en {skills}. Me interesa {job.company} porque el rol de {job.role} calza con mi búsqueda actual y con mi experiencia construyendo soluciones end-to-end.

Evidencia relevante para adaptar antes de enviar: {projects}.

Tono recomendado: {voice}

Datos a completar antes de enviar: [COMPLETAR RENTA SI APLICA], [COMPLETAR DISPONIBILIDAD SI APLICA], [COMPLETAR MOTIVO ESPECÍFICO POR LA EMPRESA].
"""
