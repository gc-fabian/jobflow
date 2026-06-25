from __future__ import annotations
from .models import Job


def email_subject(job: Job) -> str:
    return f"Postulación {job.role} – Fabián Godoy"


def application_email(job: Job, config: dict) -> str:
    c = config["candidate"]
    return f"""Estimados/as,

Junto con saludar, les envío mi postulación para el cargo de {job.role} en {job.company}.

Soy Ingeniero Civil Telemático con experiencia en desarrollo de software, backend/fullstack, APIs, bases de datos, automatización e integración de sistemas. He trabajado con Node.js, Python, JavaScript, PostgreSQL, MongoDB, Docker, Linux y herramientas de IA aplicada, conectando software con operación real y proyectos end-to-end.

Me interesa esta oportunidad porque calza con mi foco en software, producto, automatización y aprendizaje rápido. Adjunto mi CV y quedo disponible para conversar.

Saludos cordiales,
{c['name']}
{c['email']}
{c['phone']}
GitHub: {c['github']}
LinkedIn: {c['linkedin']}
"""


def form_text(job: Job, config: dict) -> str:
    return f"""Soy Ingeniero Civil Telemático orientado a Software Engineer / Backend / Fullstack, con experiencia en Node.js, Python, APIs, PostgreSQL, MongoDB, Docker, automatización, integración de sistemas e IA aplicada. Me interesa {job.company} porque el rol de {job.role} calza con mi foco en construir soluciones end-to-end, aprender rápido y aportar con criterio técnico.

Experiencia relevante: e-smart (control, telemetría e integración de sistemas), PM Custom (React Native, Python/Raspberry Pi e IoT), Laboratorios Remotos UTFSM (React, Node.js, WebSockets, JWT, ESP32, Docker y Nginx) y proyectos propios con IA aplicada.

Datos a completar antes de enviar: [COMPLETAR RENTA SI APLICA], [COMPLETAR DISPONIBILIDAD SI APLICA].
"""
