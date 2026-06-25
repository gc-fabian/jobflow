import { findJob, sendJson, readBody } from './_store.js';
export default async function handler(req, res) {
  if (req.method !== 'POST') return sendJson(res, { error: 'Method not allowed' }, 405);
  const body = await readBody(req);
  const job = findJob(body.id);
  if (!job) return sendJson(res, { error: 'Job not found' }, 404);
  job.status = 'prepared';
  job.updated_at = new Date().toISOString();
  return sendJson(res, { folder: 'Vercel demo seguro: el paquete real se genera localmente en exports/ para no subir CVs ni datos personales.' });
}
