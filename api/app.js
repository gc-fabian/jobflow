import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { getJobs, getSources, findJob, nextId, validStatus } from './_store.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');

function sendJson(res, data, status = 200) {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  res.end(JSON.stringify(data));
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      if (!body) return resolve({});
      try { resolve(JSON.parse(body)); } catch (err) { reject(err); }
    });
    req.on('error', reject);
  });
}

function requireAuth(req, res) {
  const user = process.env.AUTH_USER;
  const password = process.env.AUTH_PASSWORD;
  if (!user || !password) {
    res.statusCode = 503;
    res.setHeader('Content-Type', 'text/plain; charset=utf-8');
    res.end('AUTH_USER y AUTH_PASSWORD no están configurados en Vercel.');
    return false;
  }
  const header = req.headers.authorization || '';
  const [scheme, encoded] = header.split(' ');
  if (scheme !== 'Basic' || !encoded) {
    res.statusCode = 401;
    res.setHeader('WWW-Authenticate', 'Basic realm="JobFlow Fabian", charset="UTF-8"');
    res.end('Authentication required');
    return false;
  }
  let decoded = '';
  try { decoded = Buffer.from(encoded, 'base64').toString('utf8'); } catch (_) {}
  const separator = decoded.indexOf(':');
  const actualUser = decoded.slice(0, separator);
  const actualPassword = decoded.slice(separator + 1);
  if (actualUser !== user || actualPassword !== password) {
    res.statusCode = 401;
    res.setHeader('WWW-Authenticate', 'Basic realm="JobFlow Fabian", charset="UTF-8"');
    res.end('Credenciales inválidas');
    return false;
  }
  return true;
}

function sendIndex(res) {
  const html = fs.readFileSync(path.join(ROOT, 'web', 'index.html'), 'utf8');
  res.statusCode = 200;
  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  res.end(html);
}

export default async function handler(req, res) {
  if (!requireAuth(req, res)) return;
  const url = new URL(req.url, 'https://jobflow.local');
  const route = url.pathname.replace(/\/$/, '') || '/';

  if (req.method === 'GET' && (route === '/' || route === '/web/index.html')) return sendIndex(res);

  if (route === '/api/jobs' && req.method === 'GET') {
    return sendJson(res, getJobs().sort((a, b) => (a.status === 'discarded') - (b.status === 'discarded') || b.score - a.score));
  }
  if (route === '/api/jobs' && req.method === 'POST') {
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
  if (route === '/api/sources') return sendJson(res, getSources());
  if (route === '/api/scan') return sendJson(res, {
    scanned_at: new Date().toISOString(),
    scanned: 0,
    skipped_login: 0,
    added: 0,
    updated: 0,
    ignored_listing_pages: 0,
    errors: ['Despliegue Vercel en modo seguro/demo: el escaneo real corre localmente para no guardar credenciales ni datos personales en la nube.']
  });
  if (route === '/api/score') return sendJson(res, { ok: true, count: getJobs().length });
  if (route === '/api/status' && req.method === 'POST') {
    const body = await readBody(req);
    const job = findJob(body.id);
    if (!job) return sendJson(res, { error: 'Job not found' }, 404);
    if (!validStatus(body.status)) return sendJson(res, { error: 'Invalid status' }, 400);
    job.status = body.status;
    job.updated_at = new Date().toISOString();
    return sendJson(res, job);
  }
  if (route === '/api/package' && req.method === 'POST') {
    const body = await readBody(req);
    const job = findJob(body.id);
    if (!job) return sendJson(res, { error: 'Job not found' }, 404);
    job.status = 'prepared';
    job.updated_at = new Date().toISOString();
    return sendJson(res, { folder: 'Vercel demo seguro: el paquete real se genera localmente en exports/ para no subir CVs ni datos personales.' });
  }
  return sendJson(res, { error: 'Not found' }, 404);
}
