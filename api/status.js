import { findJob, sendJson, readBody, validStatus } from './_store.js';
export default async function handler(req, res) {
  if (req.method !== 'POST') return sendJson(res, { error: 'Method not allowed' }, 405);
  const body = await readBody(req);
  const job = findJob(body.id);
  if (!job) return sendJson(res, { error: 'Job not found' }, 404);
  if (!validStatus(body.status)) return sendJson(res, { error: 'Invalid status' }, 400);
  job.status = body.status;
  job.updated_at = new Date().toISOString();
  return sendJson(res, job);
}
