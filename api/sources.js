import { getSources, sendJson } from './_store.js';
export default function handler(req, res) { return sendJson(res, getSources()); }
