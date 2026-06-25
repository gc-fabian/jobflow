import { getJobs, getSources, sendJson } from './_store.js';
export default function handler(req, res) {
  const jobs = getJobs();
  return sendJson(res, {
    search_plan: {
      how_it_searches: ['Modo demo protegido en Vercel.', 'El scanner real se ejecuta localmente.'],
      why_not_everything_appears: ['No se ejecuta scraping real en producción demo para evitar credenciales/datos personales.'],
      configured_sources: 0,
      login_required_sources: 0,
      public_sources: 0,
      target_companies: []
    },
    last_scan: { events: [{ status: 'info', stage: 'vercel-demo', message: 'El debug completo está disponible en el dashboard local.' }] },
    sources: getSources(),
    job_count: jobs.length,
    status_counts: jobs.reduce((acc, job) => ({ ...acc, [job.status]: (acc[job.status] || 0) + 1 }), {}),
    channel_counts: jobs.reduce((acc, job) => ({ ...acc, [job.channel]: (acc[job.channel] || 0) + 1 }), {}),
    top_jobs: jobs.slice(0, 10)
  });
}
