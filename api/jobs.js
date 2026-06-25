import { getJobs, sendJson, readBody, nextId } from './_store.js';

export default async function handler(req, res) {
  if (req.method === 'GET') return sendJson(res, getJobs().sort((a, b) => (a.status === 'discarded') - (b.status === 'discarded') || b.score - a.score));
  if (req.method === 'POST') {
    const body = await readBody(req);
    const now = new Date().toISOString();
    const job = {
      id: nextId(),
      company: body.company || '[COMPLETAR EMPRESA]',
      role: body.role || '[COMPLETAR CARGO]',
      url: body.url || '[COMPLETAR URL]',
      source: 'manual-vercel',
      location: '[COMPLETAR]',
      description: body.description || '',
      status: 'new',
      score: 0,
      reasons: ['agregada manualmente en despliegue protegido'],
      risks: ['los cambios en Vercel demo son temporales; usa local para seguimiento persistente'],
      channel: body.url ? 'Portal empresa / web' : '[COMPLETAR CANAL]',
      created_at: now,
      updated_at: now,
      last_seen_at: ''
    };
    getJobs().push(job);
    return sendJson(res, job, 201);
  }
  return sendJson(res, { error: 'Method not allowed' }, 405);
}
