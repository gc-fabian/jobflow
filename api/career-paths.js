export function careerPathsPayload() {
  return {
    candidate: 'Fabián',
    generated_from_jobs: 0,
    summary: 'Demo Vercel: el análisis real usa los datos locales privados.',
    recommended_focus: [],
    paths: [
      {
        id: 'backend_api',
        title: 'Backend / API Engineer',
        fit_score: 82,
        why: 'Ruta fuerte por Python, Node, APIs, SQL y automatización.',
        current_strengths: ['Python/Node', 'APIs', 'automatización'],
        gaps: ['testing backend', 'cloud básico', 'observabilidad'],
        next_30_days: ['API con auth + tests', 'SQL/PostgreSQL práctico'],
        next_60_days: ['Docker + CI', 'jobs background y logs'],
        next_90_days: ['deploy con Postgres', 'caso técnico documentado'],
        portfolio_project: 'API de oportunidades laborales con deduplicación y scoring.',
        search_queries: ['backend developer junior chile python', 'node.js backend developer remoto latam'],
        evidence_jobs: []
      },
      {
        id: 'ai_automation',
        title: 'AI Automation / Applied AI Junior',
        fit_score: 78,
        why: 'Diferenciador por agentes, scraping ético, ranking y human-in-the-loop.',
        current_strengths: ['automatización aplicada', 'tool use', 'criterio de seguridad'],
        gaps: ['evaluación LLM', 'RAG/embeddings', 'control de costo'],
        next_30_days: ['agente pequeño con presupuesto', 'logs y límites éticos'],
        next_60_days: ['clasificación semántica opcional', 'evaluaciones buenas/malas'],
        next_90_days: ['demo de research agent con dashboard'],
        portfolio_project: 'Research Agent local que descubre empresas y recomienda oportunidades.',
        search_queries: ['ai automation engineer junior remote', 'applied ai engineer junior latam'],
        evidence_jobs: []
      }
    ]
  };
}
