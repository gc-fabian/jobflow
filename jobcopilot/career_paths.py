from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .models import Job


@dataclass(frozen=True)
class CareerTemplate:
    id: str
    title: str
    why: str
    keywords: tuple[str, ...]
    current_strengths: tuple[str, ...]
    gaps: tuple[str, ...]
    next_30_days: tuple[str, ...]
    next_60_days: tuple[str, ...]
    next_90_days: tuple[str, ...]
    portfolio_project: str
    search_queries: tuple[str, ...]


CAREERS = [
    CareerTemplate(
        id="backend_api",
        title="Backend / API Engineer",
        why="Camino fuerte para Fabián si quiere maximizar Node, Python, APIs, PostgreSQL y automatización.",
        keywords=("backend", "api", "node", "python", "django", "fastapi", "postgres", "sql", "microservice"),
        current_strengths=("Node/Python", "APIs", "automatización", "base fullstack"),
        gaps=("testing backend consistente", "cloud básico", "observabilidad/logs", "diseño de sistemas pequeño"),
        next_30_days=("Publicar 1 API REST con auth, tests y README", "Practicar SQL/PostgreSQL con queries reales", "Agregar pytest/jest a un proyecto existente"),
        next_60_days=("Dockerizar la API", "Agregar CI simple", "Implementar colas/jobs background y logs estructurados"),
        next_90_days=("Deploy con Postgres gestionado", "Documentar decisiones técnicas", "Preparar historias STAR de debugging y performance"),
        portfolio_project="API de oportunidades laborales con deduplicación, scoring y auditoría de fuentes.",
        search_queries=("backend developer junior chile python", "node.js backend developer remoto latam", "api developer semi senior chile"),
    ),
    CareerTemplate(
        id="fullstack_product",
        title="Full Stack / Product Engineer",
        why="Buen camino si quiere mostrar impacto completo: interfaz, backend, datos y decisiones de producto.",
        keywords=("fullstack", "full stack", "react", "next", "typescript", "frontend", "product engineer", "node"),
        current_strengths=("React/Next", "producto privado real", "automatización de flujo completo", "criterio UX práctico"),
        gaps=("testing de UI", "accesibilidad", "estado/cache", "deploy y monitoreo"),
        next_30_days=("Pulir una app con flujo mobile-first", "Agregar estados vacíos/carga/error", "Crear 3 tests de componentes o flujos críticos"),
        next_60_days=("Agregar analytics local/no invasivo de uso", "Mejorar performance y responsive", "Documentar arquitectura frontend/backend"),
        next_90_days=("Publicar demo privada protegida", "Preparar caso de estudio del producto", "Practicar entrevistas de tradeoffs producto/técnica"),
        portfolio_project="Dashboard JobFlow con fuentes, ranking, carrera recomendada y paquetes de postulación.",
        search_queries=("full stack developer junior chile react node", "product engineer junior remote latam", "next.js developer chile"),
    ),
    CareerTemplate(
        id="ai_automation",
        title="AI Automation / Applied AI Engineer Junior",
        why="Diferenciador fuerte: combina software con agentes, scraping ético, ranking y human-in-the-loop.",
        keywords=("ai", "ia", "llm", "automation", "agent", "agents", "openai", "prompt", "rag", "workflow"),
        current_strengths=("automatización aplicada", "human-in-the-loop", "integración de herramientas", "criterio de seguridad"),
        gaps=("evaluación de LLMs", "cost control", "RAG/embeddings", "guardrails y privacidad"),
        next_30_days=("Crear un agente pequeño con presupuesto y logs", "Medir costo por corrida", "Documentar límites éticos/no-login"),
        next_60_days=("Agregar clasificación semántica opcional", "Crear evaluaciones con ejemplos buenos/malos", "Cachear resultados y explicar decisiones"),
        next_90_days=("Construir demo de agente investigador con dashboard", "Preparar caso de ahorro de tiempo/costo", "Estudiar patrones RAG y tool calling"),
        portfolio_project="Research Agent local que descubre empresas, normaliza evidencia y recomienda oportunidades.",
        search_queries=("ai automation engineer junior remote", "applied ai engineer junior latam", "workflow automation developer chile"),
    ),
    CareerTemplate(
        id="data_analytics_engineer",
        title="Data / Analytics Engineer Junior",
        why="Camino afín si quiere usar Python, SQL y automatización para datos, reportes y pipelines.",
        keywords=("data", "analytics", "sql", "python", "etl", "bi", "dashboard", "power bi", "pipeline"),
        current_strengths=("Python", "normalización de datos", "dashboards", "SQLite/SQL inicial"),
        gaps=("SQL avanzado", "modelado dimensional", "orquestación ETL", "visualización ejecutiva"),
        next_30_days=("Practicar SQL con datasets reales", "Crear métricas de calidad de datos", "Limpiar HTML/ruido de textos"),
        next_60_days=("Construir pipeline incremental", "Agregar tablas históricas", "Crear dashboard de cobertura y tendencias"),
        next_90_days=("Publicar caso de datos end-to-end", "Aprender dbt básico o equivalente", "Preparar historias de calidad/deduplicación"),
        portfolio_project="Pipeline SQLite de ofertas: raw observations, normalized jobs, scans, quality metrics.",
        search_queries=("data analyst python sql junior chile", "analytics engineer junior remote latam", "data engineer junior python chile"),
    ),
    CareerTemplate(
        id="qa_automation",
        title="QA Automation / SDET Junior",
        why="Ruta realista si se quiere entrar por testing automatizado y luego moverse a backend/fullstack.",
        keywords=("qa", "quality", "tester", "automation", "selenium", "playwright", "pytest", "cypress", "sdet"),
        current_strengths=("automatización", "debugging", "tests de regresión", "criterio de flujo usuario"),
        gaps=("Playwright/Cypress formal", "estrategia de test", "reportes CI", "testing API"),
        next_30_days=("Agregar tests de API y scanner", "Crear prueba e2e de dashboard", "Documentar bugs encontrados y fixes"),
        next_60_days=("Integrar tests en CI", "Aprender Playwright básico", "Crear matriz de smoke tests"),
        next_90_days=("Preparar portfolio QA con bugs reales", "Automatizar flujos críticos", "Practicar entrevistas de testing"),
        portfolio_project="Suite de regresión JobFlow: scan, deduplicación, API, UI de dashboard.",
        search_queries=("qa automation junior chile python", "sdet junior remote latam", "playwright tester junior"),
    ),
]


def _tokens(values: list[str]) -> set[str]:
    out: set[str] = set()
    for value in values:
        for token in str(value).replace("/", " ").replace("-", " ").split():
            clean = token.strip().lower()
            if len(clean) > 2:
                out.add(clean)
    return out


def career_paths_report(config: dict, jobs: list[Job]) -> dict:
    candidate = config.get("candidate", {})
    profile_values = []
    for key in ["target_roles", "skills_core", "skills_plus", "skills_learning", "headline", "base_profile"]:
        value = candidate.get(key, [])
        profile_values.extend(value if isinstance(value, list) else [value])
    profile_tokens = _tokens(profile_values)
    job_texts = [" ".join([job.role, job.company, job.description, job.channel]).lower() for job in jobs]
    role_counts = Counter()
    for template in CAREERS:
        evidence_jobs = []
        for job, text in zip(jobs, job_texts):
            hits = [kw for kw in template.keywords if kw in text]
            if hits:
                role_counts[template.id] += len(hits)
                if len(evidence_jobs) < 6:
                    evidence_jobs.append({
                        "id": job.id,
                        "company": job.company,
                        "role": job.role,
                        "score": job.score,
                        "url": job.url,
                        "matched_keywords": hits[:5],
                    })
        profile_hits = [kw for kw in template.keywords if kw in profile_tokens or any(kw in token for token in profile_tokens)]
        market_signal = min(100, role_counts[template.id] * 2)
        profile_signal = min(40, len(profile_hits) * 8)
        score = min(100, 20 + market_signal + profile_signal)
        if evidence_jobs:
            score = min(100, score + 10)
        yield {
            "id": template.id,
            "title": template.title,
            "fit_score": score,
            "why": template.why,
            "market_matches": role_counts[template.id],
            "profile_matches": profile_hits,
            "current_strengths": list(template.current_strengths),
            "gaps": list(template.gaps),
            "next_30_days": list(template.next_30_days),
            "next_60_days": list(template.next_60_days),
            "next_90_days": list(template.next_90_days),
            "portfolio_project": template.portfolio_project,
            "search_queries": list(template.search_queries),
            "evidence_jobs": evidence_jobs,
        }


def build_career_paths(config: dict, jobs: list[Job]) -> dict:
    paths = sorted(career_paths_report(config, jobs), key=lambda item: item["fit_score"], reverse=True)
    return {
        "candidate": config.get("candidate", {}).get("name", "Fabián"),
        "generated_from_jobs": len(jobs),
        "summary": "Rutas afines calculadas desde el perfil del usuario, skills declaradas y señales de las ofertas guardadas.",
        "recommended_focus": paths[:3],
        "paths": paths,
    }
