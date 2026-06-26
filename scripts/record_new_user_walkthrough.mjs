import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const ROOT = path.resolve(process.cwd());
const VIDEO_DIR = path.join(ROOT, 'exports', 'walkthrough_nuevo_usuario');
const RAW_DIR = path.join(VIDEO_DIR, 'raw_node');
const FINAL_WEBM = path.join(VIDEO_DIR, 'jobflow_walkthrough_nuevo_usuario.webm');
const URL = process.env.JOBFLOW_URL || 'http://127.0.0.1:8765';
fs.mkdirSync(VIDEO_DIR, { recursive: true });
fs.rmSync(RAW_DIR, { recursive: true, force: true });
fs.mkdirSync(RAW_DIR, { recursive: true });

async function caption(page, title, body='') {
  await page.evaluate(({title, body}) => {
    let el = document.getElementById('walkthrough-caption');
    if (!el) {
      el = document.createElement('div');
      el.id = 'walkthrough-caption';
      el.style.cssText = [
        'position:fixed','left:26px','bottom:24px','z-index:99999','max-width:760px',
        'background:rgba(17,24,39,.94)','color:white','padding:18px 22px','border-radius:20px',
        'font:600 20px/1.35 Inter,system-ui,Arial,sans-serif','box-shadow:0 24px 80px rgba(0,0,0,.38)',
        'border:1px solid rgba(255,255,255,.22)'
      ].join(';');
      document.body.appendChild(el);
    }
    el.innerHTML = `<div style="font-size:23px;font-weight:850;margin-bottom:6px">${title}</div>` +
      (body ? `<div style="font-size:16px;font-weight:500;opacity:.92">${body}</div>` : '');
  }, {title, body});
  await page.waitForTimeout(2100);
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
  recordVideo: { dir: RAW_DIR, size: { width: 1440, height: 1000 } },
  locale: 'es-CL'
});
const page = await context.newPage();
page.on('dialog', d => d.accept());
await page.goto(URL, { waitUntil: 'networkidle' });
await page.waitForSelector('article.job', { timeout: 30000 });
await caption(page, 'JobFlow by Corocul', 'Walkthrough para un usuario nuevo: buscar, revisar y preparar postulaciones sin enviar nada automáticamente.');
await caption(page, '1. Panel principal', 'A la izquierda agregas ofertas, revisas el perfil candidato y ves el estado del escaneo.');
await page.mouse.wheel(0, 260); await page.waitForTimeout(900); await page.mouse.wheel(0, -260);
await caption(page, '2. Usuario candidato', 'Este perfil sensibiliza la búsqueda: roles objetivo, skills, restricciones y tono honesto de postulación.');
await page.locator('summary', { hasText: 'Editar perfil sensibilizado' }).click(); await page.waitForTimeout(1600);
await page.locator('summary', { hasText: 'Editar perfil sensibilizado' }).click();
await caption(page, '3. Agregar una oferta', 'Pega empresa, cargo, link y descripción desde LinkedIn, GetOnBoard, AIRA u otro portal.');
await page.fill('#company', 'Empresa Demo'); await page.fill('#role', 'Full Stack Developer'); await page.fill('#url', 'https://example.com/jobs/fullstack');
await page.fill('#description', 'Node.js, TypeScript, React, SQL, APIs, integración de sistemas. Oferta demo para walkthrough.');
await page.waitForTimeout(1300);
await page.fill('#company', ''); await page.fill('#role', ''); await page.fill('#url', ''); await page.fill('#description', '');
await caption(page, '4. Mejores opciones', 'Cada oferta muestra score, razones de calce, brechas y estado para decidir con criterio.');
await page.mouse.wheel(0, 450); await page.waitForTimeout(1200); await page.mouse.wheel(0, -250);
await caption(page, '5. Debug de búsqueda', 'Permite ver dónde buscó, qué entró, qué se omitió y por qué. Útil para mejorar fuentes.');
await page.locator('text=Debug búsqueda').click(); await page.waitForTimeout(1600);
await caption(page, '6. Crear postulación', 'El botón genera paquete local: CV ATS PDF/TXT/MD, correo, mensaje, checklist y notas de revisión.');
await page.waitForSelector('button[onclick^="packageJob"]', { timeout: 30000 });
await page.locator('button[onclick^="packageJob"]').first().click(); await page.waitForTimeout(1700);
await caption(page, '7. Regla de seguridad', 'JobFlow prepara; el usuario revisa y envía. No guarda contraseñas ni postula automáticamente.');
await page.waitForTimeout(2200);
const video = page.video();
await context.close();
await browser.close();
const rawPath = await video.path();
fs.copyFileSync(rawPath, FINAL_WEBM);
console.log('WEBM=' + FINAL_WEBM);
