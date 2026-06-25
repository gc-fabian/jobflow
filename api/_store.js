const seedJobs = [
  {
    id: 1,
    company: 'Ejemplo seguro',
    role: 'Software Engineer / Backend Junior',
    url: 'https://example.com/jobs/software-engineer',
    source: 'demo',
    location: 'Chile / remoto',
    description: 'Oferta demo para verificar el dashboard desplegado. En local se usan tus datos reales; en Vercel no se suben data/jobs.json, exports, CVs ni config.json.',
    status: 'new',
    score: 72,
    reasons: ['+ rol objetivo', '+ backend/API', '+ modalidad flexible'],
    risks: ['demo público protegido: reemplazar con datos reales solo si decides conectar una base segura'],
    channel: 'Demo / portal empresa',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    last_seen_at: new Date().toISOString()
  }
];

const seedSources = {
  searches: [
    { name: 'LinkedIn - búsqueda manual', url: 'https://www.linkedin.com/jobs/search/', login_required: true, priority: 1 },
    { name: 'Get on Board - software', url: 'https://www.getonbrd.com/empleos/programacion', login_required: false, priority: 1 }
  ],
  company_links: [
    { company: 'Global66', careers_search: 'https://www.google.com/search?q=Global66+careers+software+Chile' },
    { company: 'Buk', careers_search: 'https://www.google.com/search?q=Buk+careers+software+Chile' },
    { company: 'Fintoc', careers_search: 'https://www.google.com/search?q=Fintoc+careers+software+Chile' },
    { company: 'Get on Board', careers_search: 'https://www.getonbrd.com/empleos/programacion' }
  ]
};


const seedProfile = {
  name: '[COMPLETAR NOMBRE]',
  email: '[COMPLETAR EMAIL]',
  phone: '[COMPLETAR TELÉFONO]',
  linkedin: '[COMPLETAR LINKEDIN]',
  github: '[COMPLETAR GITHUB]',
  portfolio: '[COMPLETAR PORTFOLIO]',
  headline: 'Software Engineer / Backend / Fullstack orientado a automatización e IA aplicada',
  target_roles: ['Software Engineer', 'Backend Developer', 'Full Stack Developer', 'Product Engineer', 'AI Engineer Junior'],
  seniority_target: 'junior / semi senior inicial / 0-3 años',
  preferred_work_modes: ['remoto', 'híbrido', 'Santiago', 'Chile', 'LatAm remoto'],
  locations: ['Chile', 'Santiago', 'Remoto LatAm'],
  skills_core: ['Python', 'Node.js', 'JavaScript', 'TypeScript', 'APIs', 'PostgreSQL', 'SQL', 'Docker', 'React', 'Linux', 'Git'],
  skills_plus: ['IA aplicada', 'automatización', 'integración de sistemas', 'IoT', 'WebSockets', 'JWT', 'MongoDB'],
  deal_breakers: ['senior puro', 'lead/head/manager', '5+ años excluyente', 'solo mobile senior', 'práctica no remunerada'],
  evidence_projects: ['Automatización de bombas por niveles de agua', 'Laboratorios remotos', 'Asistentes y dashboards privados con IA aplicada'],
  application_voice: 'Profesional, honesto, breve; no exagerar seniority ni inventar certificaciones.'
};

let jobs = globalThis.__jobflowJobs || seedJobs.map(job => ({ ...job }));
globalThis.__jobflowJobs = jobs;
let profile = globalThis.__jobflowProfile || { ...seedProfile };
globalThis.__jobflowProfile = profile;

export function sendJson(res, data, status = 200) {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  res.end(JSON.stringify(data));
}

export function readBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      if (!body) return resolve({});
      try { resolve(JSON.parse(body)); }
      catch (err) { reject(err); }
    });
    req.on('error', reject);
  });
}

export function getJobs() { return jobs; }
export function getSources() { return seedSources; }
export function getProfile() { return profile; }
export function setProfile(nextProfile) { profile = { ...profile, ...nextProfile }; globalThis.__jobflowProfile = profile; return profile; }
export function findJob(id) { return jobs.find(job => job.id === Number(id)); }
export function nextId() { return Math.max(0, ...jobs.map(job => job.id || 0)) + 1; }
export function validStatus(status) { return ['new','reviewed','prepared','sent','discarded','requires_info'].includes(status); }
