from __future__ import annotations

import re
from pathlib import Path
from .models import Job

ATS_TEMPLATE_VERSION = "ats-professional-v1"


def _safe_slug(text: str) -> str:
    keep = []
    for ch in text.lower():
        if ch.isalnum():
            keep.append(ch)
        elif ch in " -_/":
            keep.append("_")
    return "_".join("".join(keep).split("_"))[:80]


def _contains_any(text: str, words: list[str]) -> bool:
    low = text.lower()
    return any(w.lower() in low for w in words)


def _job_keywords(job: Job) -> dict[str, bool]:
    text = " ".join([job.role, job.company, job.description, job.location]).lower()
    return {
        "node": "node" in text or "backend" in text,
        "typescript": "typescript" in text or "type script" in text,
        "react": "react" in text,
        "retail": "retail" in text or "e-commerce" in text or "ecommerce" in text or "catálogo" in text,
        "cloud": "aws" in text or "gcp" in text or "azure" in text or "cloud" in text,
        "english": "inglés" in text or "english" in text,
        "onsite": "presencial" in text or "on-site" in text or "onsite" in text or "las condes" in text,
    }


def build_cv_profile(job: Job, config: dict) -> dict:
    candidate = config.get("candidate", {})
    flags = _job_keywords(job)
    name = candidate.get("name", "Fabián Esteban Godoy Casas")
    email = candidate.get("email", "fabian.godoyc@sansano.usm.cl")
    phone = candidate.get("phone", "")
    linkedin = candidate.get("linkedin", "https://www.linkedin.com/in/fgodoycasas/")
    github = candidate.get("github", "https://github.com/gc-fabian")
    headline_bits = ["Full Stack Developer"]
    if flags["node"]:
        headline_bits.append("Node.js")
    if flags["typescript"]:
        headline_bits.append("TypeScript")
    if flags["react"]:
        headline_bits.append("React")
    headline_bits.extend(["SQL", "APIs", "Integración de Sistemas"])
    profile = (
        "Ingeniero Civil Telemático con experiencia en desarrollo full-stack, backend, APIs, "
        "automatización e integración de sistemas. He trabajado con Node.js, JavaScript/TypeScript, "
        "React, React Native, PostgreSQL, MongoDB, Docker, Linux y WebSockets, conectando software "
        "con operación real, datos y usuarios."
    )
    if flags["retail"]:
        profile += " Me interesa aportar en plataformas internas, retail, e-commerce e integración de sistemas críticos."
    else:
        profile += " Me interesa aportar en productos claros, confiables y orientados a usuarios."
    skills = {
        "Desarrollo": ["Node.js", "JavaScript", "TypeScript", "Python", "React", "React Native", "HTML5", "CSS3", "APIs REST", "JWT", "WebSockets"],
        "Datos e integración": ["PostgreSQL", "SQL", "MongoDB", "SQLite", "integración de APIs", "flujos de datos"],
        "Infra y herramientas": ["Docker", "Docker Compose", "Linux", "Nginx", "Apache", "Git", "GitHub", "documentación técnica", "QA funcional"],
        "Diferenciales": ["automatización", "IoT", "Node-RED", "MQTT", "Modbus", "integración con hardware", "LLMs", "asistentes internos"],
    }
    warnings = []
    if flags["cloud"]:
        warnings.append("La oferta pide cloud AWS/GCP/Azure: mencionar solo experiencia real o tratarlo como brecha/aprendizaje.")
    if flags["english"]:
        warnings.append("La oferta exige inglés: confirmar que el nivel declarado se sostiene en entrevista.")
    if flags["onsite"]:
        warnings.append("Confirmar disponibilidad presencial/híbrida antes de enviar.")
    if _contains_any(job.description + " " + job.role, ["senior", "lead", "head", "5+ años"]):
        warnings.append("Rol senior/stretch: no inflar seniority; destacar evidencia técnica y ownership real.")
    return {
        "template": ATS_TEMPLATE_VERSION,
        "name": name,
        "contact": " | ".join(x for x in [email, phone, linkedin, github] if x),
        "headline": " | ".join(dict.fromkeys(headline_bits)),
        "profile": profile,
        "skills": skills,
        "warnings": warnings,
        "education": "Ingeniería Civil Telemática — Universidad Técnica Federico Santa María | 2018–2024",
        "languages": "Español nativo. Inglés avanzado/técnico. Licencia clase B.",
    }


def render_cv_markdown(job: Job, config: dict) -> str:
    cv = build_cv_profile(job, config)
    lines = [f"# {cv['name']}", cv["headline"], cv["contact"], "", "## Perfil", cv["profile"], "", "## Habilidades Técnicas"]
    for group, items in cv["skills"].items():
        lines.append(f"- **{group}:** {', '.join(items)}")
    lines += [
        "", "## Experiencia",
        "### Controller Engineer — e-smart | May 2025 – Abr 2026",
        "- Desarrollo de lógicas de control, monitoreo e integración de datos en Node-RED para sistemas de bombeo, telemetría y operación en terreno.",
        "- Integración de sensores, dataloggers, APIs/protocolos industriales y comunicaciones Modbus/MQTT para sistemas operacionales.",
        "- Diagnóstico, documentación técnica y soporte a despliegues reales, priorizando continuidad operativa, trazabilidad y confiabilidad.",
        "", "### Desarrollador Full-Stack IoT — PM Custom | Dic 2024 – Feb 2025",
        "- Desarrollo de aplicación móvil en React Native con integración IoT y funcionalidades de visión por computador.",
        "- Automatización de pruebas con Python y Raspberry Pi para validar equipos y flujos conectados a hardware.",
        "", "### Desarrollador Frontend Jr. — Falabella Retail | Abr 2023 – Jul 2023",
        "- Mantención y mejora de e-commerce Novios Falabella, resolución de tickets, QA funcional y validación de cambios en producción.",
        "- Implementación y validación de Google Tag Manager para medición de comportamiento de usuarios y soporte a equipos de negocio.",
        "", "### Ingeniero de Implementación — Haulmer SPA | Ene 2021 – Mar 2021",
        "- Migración de servidor web de Nginx a Apache y desarrollo de sistema anti-spam en Python con filtrado bayesiano.",
        "", "## Proyectos Relevantes",
        "- **Laboratorios Remotos — UTFSM:** Plataforma full-stack con React, Node.js, WebSockets, JWT, reservas, roles, ESP32, Docker y Nginx para control remoto de experimentos.",
        "- **Automatización de tres bombas por niveles de agua:** lógica de control en tiempo real con estados independientes por bomba para evitar punto muerto, acumulación de lodo, sobreextracción y ciclos frecuentes.",
        "- **Hermes / asistentes con IA:** herramientas personales con LLMs, automatización de tareas, contexto conversacional, persistencia y flujos human-in-the-loop.",
        "", "## Educación e Idiomas", cv["education"], cv["languages"],
    ]
    return "\n".join(lines) + "\n"


def render_cv_text(job: Job, config: dict) -> str:
    markdown = render_cv_markdown(job, config)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", markdown)
    return text.replace("# ", "").replace("## ", "").replace("### ", "")


def render_cv_pdf(job: Job, config: dict, folder: Path) -> Path | None:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import SimpleDocTemplate, Paragraph, HRFlowable
    except Exception:
        return None
    try:
        pdfmetrics.registerFont(TTFont("ATSRegular", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
        pdfmetrics.registerFont(TTFont("ATSBold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
        regular, bold = "ATSRegular", "ATSBold"
    except Exception:
        regular, bold = "Helvetica", "Helvetica-Bold"
    styles = {
        "name": ParagraphStyle("name", fontName=bold, fontSize=12.5, leading=14, alignment=1, spaceAfter=1),
        "head": ParagraphStyle("head", fontName=regular, fontSize=8.4, leading=10, alignment=1, spaceAfter=2),
        "section": ParagraphStyle("section", fontName=bold, fontSize=9.6, leading=11, spaceBefore=5, spaceAfter=1),
        "sub": ParagraphStyle("sub", fontName=bold, fontSize=8.2, leading=9.4, spaceBefore=2, spaceAfter=0),
        "body": ParagraphStyle("body", fontName=regular, fontSize=7.45, leading=8.75, spaceAfter=0),
    }
    def p(text: str, style: str = "body"):
        return Paragraph(text.replace("&", "&amp;"), styles[style])
    def bullet(text: str):
        return p("• " + text)
    def section(title: str):
        return [p(title, "section"), HRFlowable(width="100%", thickness=0.55, color=colors.black, spaceBefore=0, spaceAfter=2)]
    cv = build_cv_profile(job, config)
    flow = [p(cv["name"], "name"), p(cv["headline"], "head"), p(cv["contact"], "head")]
    flow += section("Perfil")
    flow.append(p(cv["profile"]))
    flow += section("Habilidades Técnicas")
    for group, items in cv["skills"].items():
        flow.append(bullet(f"<b>{group}:</b> {', '.join(items)}"))
    flow += section("Experiencia")
    experience = [
        (f"Controller Engineer — e-smart <font name='{regular}'>May 2025 — Abr 2026</font>", ["Desarrollo de lógicas de control, monitoreo e integración de datos en Node-RED para sistemas de bombeo, telemetría y operación en terreno.", "Integración de sensores, dataloggers, APIs/protocolos industriales y comunicaciones Modbus/MQTT para sistemas operacionales.", "Diagnóstico, documentación técnica y soporte a despliegues reales, priorizando continuidad operativa, trazabilidad y confiabilidad."]),
        (f"Desarrollador Full-Stack IoT — PM Custom <font name='{regular}'>Dic 2024 — Feb 2025</font>", ["Desarrollo de aplicación móvil en React Native con integración IoT y funcionalidades de visión por computador.", "Automatización de pruebas con Python y Raspberry Pi para validar equipos y flujos conectados a hardware."]),
        (f"Desarrollador Frontend Jr. — Falabella Retail <font name='{regular}'>Abr 2023 — Jul 2023</font>", ["Mantención y mejora de e-commerce Novios Falabella, resolución de tickets, QA funcional y validación de cambios en producción.", "Implementación y validación de Google Tag Manager para medición de comportamiento de usuarios y soporte a equipos de negocio."]),
        (f"Ingeniero de Implementación — Haulmer SPA <font name='{regular}'>Ene 2021 — Mar 2021</font>", ["Migración de servidor web de Nginx a Apache y desarrollo de sistema anti-spam en Python con filtrado bayesiano."]),
    ]
    for title, bullets in experience:
        flow.append(p(title, "sub"))
        for item in bullets:
            flow.append(bullet(item))
    flow += section("Proyectos Relevantes")
    for item in ["<b>Laboratorios Remotos — UTFSM:</b> Plataforma full-stack con React, Node.js, WebSockets, JWT, reservas, roles, ESP32, Docker y Nginx para control remoto de experimentos.", "<b>Automatización de tres bombas por niveles de agua:</b> lógica de control en tiempo real con estados independientes por bomba para evitar punto muerto, acumulación de lodo, sobreextracción y ciclos frecuentes.", "<b>Hermes / asistentes con IA:</b> herramientas personales con LLMs, automatización de tareas, contexto conversacional, persistencia y flujos human-in-the-loop."]:
        flow.append(bullet(item))
    flow += section("Educación e Idiomas")
    flow.append(p(f"<b>{cv['education']}</b>"))
    flow.append(p(cv["languages"]))
    pdf_path = folder / f"CV_Fabian_Godoy_{_safe_slug(job.company)}_ATS.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, leftMargin=1.12 * cm, rightMargin=1.12 * cm, topMargin=1.0 * cm, bottomMargin=1.0 * cm)
    doc.build(flow)
    return pdf_path


def write_cv_package(job: Job, config: dict, folder: Path) -> dict[str, str]:
    folder.mkdir(parents=True, exist_ok=True)
    base = f"CV_Fabian_Godoy_{_safe_slug(job.company)}"
    md = folder / f"{base}_ATS.md"
    txt = folder / f"{base}_ATS.txt"
    md.write_text(render_cv_markdown(job, config), encoding="utf-8")
    txt.write_text(render_cv_text(job, config), encoding="utf-8")
    pdf = render_cv_pdf(job, config, folder)
    cv = build_cv_profile(job, config)
    warnings = "\n".join(f"- {w}" for w in cv["warnings"]) or "- Sin advertencias críticas detectadas por la plantilla."
    review = folder / "cv_review_notes.md"
    review.write_text(f"""# Revisión CV — {job.company} / {job.role}

Plantilla: {ATS_TEMPLATE_VERSION}

Archivo principal sugerido:
- {pdf.name if pdf else md.name}

Archivos para bots/ATS:
- {txt.name}
- {md.name}

Advertencias antes de enviar:
{warnings}

Reglas de la plantilla:
- Una página.
- Sin columnas complejas.
- Sin gráficos, foto ni barras de habilidad.
- Keywords visibles para ATS.
- No inventa cloud, seniority ni certificaciones.
""", encoding="utf-8")
    return {"pdf": pdf.name if pdf else "", "markdown": md.name, "text": txt.name, "review": review.name}
