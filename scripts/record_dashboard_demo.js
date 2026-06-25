const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const ROOT = 'C:/Users/56989/Documents/job-application-copilot';
const VIDEO_DIR = path.join(ROOT, 'exports', 'dashboard_demo_video');
const RAW_DIR = path.join(VIDEO_DIR, 'raw-node');
const FINAL_WEBM = path.join(VIDEO_DIR, 'jobcopilot_dashboard_demo.webm');
const URL = 'http://172.20.100.17:8765';

function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

async function caption(page, text) {
  await page.evaluate((message) => {
    let el = document.getElementById('demo-caption');
    if (!el) {
      el = document.createElement('div');
      el.id = 'demo-caption';
      el.style.cssText = [
        'position:fixed', 'left:28px', 'bottom:28px', 'z-index:99999',
        'max-width:760px', 'background:rgba(23,23,23,.92)', 'color:white',
        'padding:16px 20px', 'border-radius:18px', 'font:700 22px/1.35 Inter, system-ui, sans-serif',
        'box-shadow:0 20px 70px rgba(0,0,0,.35)', 'border:1px solid rgba(255,255,255,.18)'
      ].join(';');
      document.body.appendChild(el);
    }
    el.textContent = message;
  }, text);
  await sleep(1700);
}

async function main() {
  fs.mkdirSync(VIDEO_DIR, { recursive: true });
  fs.rmSync(RAW_DIR, { recursive: true, force: true });
  fs.mkdirSync(RAW_DIR, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
    recordVideo: { dir: RAW_DIR, size: { width: 1440, height: 1000 } },
    locale: 'es-CL',
  });
  const page = await context.newPage();
  page.on('dialog', async dialog => { await sleep(900); await dialog.accept(); });

  await page.goto(URL, { waitUntil: 'networkidle' });
  await caption(page, 'Job Copilot local: dashboard de búsqueda laboral para Fabián. Nada se envía sin confirmación humana.');

  await caption(page, '1) Revisa las mejores ofertas: empresa, cargo, score, canal y estado.');
  await page.mouse.wheel(0, 420);
  await sleep(1200);
  await page.mouse.wheel(0, -420);
  await sleep(800);

  await caption(page, '2) Usa el filtro para enfocarte en una empresa u oferta concreta.');
  await page.fill('#q', 'Devaid');
  await sleep(1400);
  await page.fill('#q', '');
  await sleep(900);

  await caption(page, '3) Ejecuta un escaneo público: omite LinkedIn/login y no guarda credenciales.');
  await page.getByText('Escanear fuentes públicas').click();
  try {
    await page.waitForFunction(() => document.querySelector('#scanState')?.textContent.includes('escaneadas'), { timeout: 45000 });
  } catch (_) {}
  await sleep(1200);

  await caption(page, '4) Revisa razones de calce y riesgos/brechas antes de preparar una postulación.');
  await page.fill('#q', 'Devaid');
  await sleep(900);
  await page.locator('article.job details summary').first().click();
  await sleep(1300);

  await caption(page, '5) Crea un paquete local: CV sugerido, correo, mensaje de formulario, checklist y postulacion.md.');
  await page.locator('article.job button:has-text("Crear postulación")').first().click();
  await sleep(1800);

  await caption(page, '6) Cambia estados manualmente: revisada, requiere dato, descartada o enviada. Enviar sigue siendo decisión humana.');
  await sleep(1500);

  await caption(page, 'Listo: el tracker local se actualiza y el dashboard queda como centro seguro de postulaciones.');
  await sleep(2000);

  const video = page.video();
  await context.close();
  await browser.close();
  const rawPath = await video.path();
  fs.copyFileSync(rawPath, FINAL_WEBM);
  console.log('WEBM=' + FINAL_WEBM);
}

main().catch(err => { console.error(err); process.exit(1); });
