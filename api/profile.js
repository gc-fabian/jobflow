import { getProfile, setProfile, sendJson, readBody } from './_store.js';

export default async function handler(req, res) {
  if (req.method === 'POST') {
    const body = await readBody(req);
    const candidate = body.candidate && typeof body.candidate === 'object' ? body.candidate : body;
    return sendJson(res, {
      candidate: setProfile(candidate),
      search_behavior: ['Demo Vercel: perfil editable en memoria; en local se guarda en config.json.']
    });
  }
  const candidate = getProfile();
  return sendJson(res, {
    candidate,
    summary: {
      headline: candidate.headline,
      target_roles: candidate.target_roles,
      core_skills: candidate.skills_core,
      plus_skills: candidate.skills_plus,
      deal_breakers: candidate.deal_breakers,
      work_modes: candidate.preferred_work_modes,
      locations: candidate.locations
    },
    search_behavior: ['Perfil candidato usado para orientar búsqueda, scoring y texto de postulación.']
  });
}
