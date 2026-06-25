from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from .models import Job

TRACKER_NAME = "POSTULACIONES_TRACKER.md"
STATUS_LABELS = {
    "new": "nueva",
    "reviewed": "revisada",
    "prepared": "preparada",
    "sent": "enviada",
    "discarded": "descartada",
    "requires_info": "requiere dato",
}


def write_tracker(root: Path, jobs: list[Job]) -> Path:
    path = root / TRACKER_NAME
    counts = Counter(j.status for j in jobs)
    lines = [
        "# Tracker de postulaciones — Fabián Godoy",
        "",
        f"Última actualización: {datetime.now(timezone.utc).isoformat()}",
        "",
        "Regla de seguridad: ningún correo, formulario o botón final de postulación se envía sin confirmación explícita de Fabián.",
        "",
        "## Resumen",
        "",
    ]
    if jobs:
        for status, label in STATUS_LABELS.items():
            lines.append(f"- {label}: {counts.get(status, 0)}")
    else:
        lines.append("- Sin ofertas registradas todavía.")
    lines.extend([
        "",
        "## Ofertas",
        "",
        "| ID | Estado | Score | Empresa | Cargo | Canal | Link |",
        "|---:|---|---:|---|---|---|---|",
    ])
    for job in sorted(jobs, key=lambda j: (j.status == "discarded", -j.score, j.company.lower())):
        status = STATUS_LABELS.get(job.status, job.status)
        link = job.url if job.url.startswith("http") else ""
        lines.append(
            f"| {job.id} | {status} | {job.score} | {_cell(job.company)} | {_cell(job.role)} | {_cell(job.channel)} | {link} |"
        )
    lines.extend([
        "",
        "## Próximo uso",
        "",
        "1. Revisar ofertas nuevas con mayor score.",
        "2. Pegar descripción completa si requiere dato o la descripción viene de LinkedIn/login.",
        "3. Crear paquete solo para ofertas con buen calce.",
        "4. Enviar o marcar enviada solo después de revisión humana.",
    ])
    path.write_text(chr(10).join(lines) + chr(10), encoding="utf-8")
    return path


def _cell(text: str) -> str:
    return (text or "").replace("|", "\|").replace(chr(10), " ")[:140]
