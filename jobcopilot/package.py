from __future__ import annotations
import shutil
from pathlib import Path
from .models import Job
from .templates import email_subject, application_email, form_text


def safe_slug(text: str) -> str:
    keep = []
    for ch in text.lower():
        if ch.isalnum():
            keep.append(ch)
        elif ch in " -_/":
            keep.append("_")
    return "_".join("".join(keep).split("_"))[:80]


def choose_cv(config: dict) -> Path | None:
    source = Path(config.get("paths", {}).get("source_cvs_dir", ""))
    if not source.exists():
        return None
    preferred = ["CV_Fabian_Godoy_FullStack.pdf", "CV_Fabian_Godoy_Backend.pdf", "CV_Fabian_Godoy_Principal.pdf"]
    for name in preferred:
        p = source / name
        if p.exists():
            return p
    pdfs = sorted(source.glob("*.pdf"))
    return pdfs[0] if pdfs else None


def create_package(job: Job, config: dict, root: Path) -> Path:
    exports = root / config.get("paths", {}).get("exports_dir", "exports")
    folder = exports / f"{job.id:03d}_{safe_slug(job.company)}_{safe_slug(job.role)}"
    folder.mkdir(parents=True, exist_ok=True)

    cv = choose_cv(config)
    cv_line = "[COMPLETAR: adjuntar CV específico]"
    if cv:
        target = folder / f"CV_Fabian_Godoy_{safe_slug(job.company)}.pdf"
        shutil.copy2(cv, target)
        cv_line = target.name

    (folder / "correo_postulacion.txt").write_text(
        f"Asunto: {email_subject(job)}\n\n{application_email(job, config)}", encoding="utf-8"
    )
    (folder / "mensaje_formulario.txt").write_text(form_text(job, config), encoding="utf-8")
    checklist = f"""# Checklist de envío

- [ ] Abrir oferta: {job.url}
- [ ] Revisar si sigue activa.
- [ ] Adjuntar CV: {cv_line}
- [ ] Copiar correo o texto de formulario.
- [ ] Completar marcadores [COMPLETAR].
- [ ] Confirmar renta si la plataforma lo pide.
- [ ] NO enviar sin revisión final de Fabián.
"""
    (folder / "checklist.md").write_text(checklist, encoding="utf-8")
    reasons = chr(10).join("- " + r for r in job.reasons) if job.reasons else "- [sin score todavía]"
    risks = chr(10).join("- " + r for r in job.risks) if job.risks else "- [sin brechas marcadas]"
    summary = f"""# Postulación — {job.company} / {job.role}

Estado: preparada / requiere revisión humana

URL: {job.url}

Canal: {job.channel}

Score: {job.score}

Razones de calce:
{reasons}

Riesgos / brechas:
{risks}

CV sugerido: {cv_line}

Archivos:
- correo_postulacion.txt
- mensaje_formulario.txt
- checklist.md
"""
    (folder / "postulacion.md").write_text(summary, encoding="utf-8")
    return folder
