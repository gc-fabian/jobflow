import { sendJson } from './_store.js';
const result = () => ({
  scanned_at: new Date().toISOString(),
  scanned: 0,
  skipped_login: 0,
  added: 0,
  updated: 0,
  ignored_listing_pages: 0,
  errors: ['Despliegue Vercel en modo seguro/demo: el escaneo real corre localmente para no guardar credenciales ni datos personales en la nube.']
});
export default function handler(req, res) { return sendJson(res, result()); }
