import { getJobs, sendJson } from './_store.js';
export default function handler(req, res) { return sendJson(res, { ok: true, count: getJobs().length }); }
