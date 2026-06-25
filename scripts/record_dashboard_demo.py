from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
VIDEO_DIR = ROOT / "exports" / "dashboard_demo_video"
RAW_DIR = VIDEO_DIR / "raw"
FINAL_WEBM = VIDEO_DIR / "jobcopilot_dashboard_demo.webm"
FINAL_MP4 = VIDEO_DIR / "jobcopilot_dashboard_demo.mp4"
URL = "http://127.0.0.1:8765"


def ensure_dashboard() -> subprocess.Popen | None:
    try:
        import urllib.request
        urllib.request.urlopen(URL, timeout=2).read(128)
        return None
    except Exception:
        proc = subprocess.Popen(
            [sys.executable, "-m", "jobcopilot", "serve", "--port", "8765", "--no-open"],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        import time
        import urllib.request
        for _ in range(30):
            try:
                urllib.request.urlopen(URL, timeout=1).read(128)
                return proc
            except Exception:
                time.sleep(0.5)
        raise RuntimeError("Dashboard no respondió en http://127.0.0.1:8765")


def caption(page, text: str) -> None:
    page.evaluate(
        """
        (text) => {
          let el = document.getElementById('demo-caption');
          if (!el) {
            el = document.createElement('div');
            el.id = 'demo-caption';
            el.style.cssText = [
              'position:fixed', 'left:28px', 'bottom:28px', 'z-index:99999',
              'max-width:720px', 'background:rgba(23,23,23,.92)', 'color:white',
              'padding:16px 20px', 'border-radius:18px', 'font:700 22px/1.35 Inter, system-ui, sans-serif',
              'box-shadow:0 20px 70px rgba(0,0,0,.35)', 'border:1px solid rgba(255,255,255,.18)'
            ].join(';');
            document.body.appendChild(el);
          }
          el.textContent = text;
        }
        """,
        text,
    )
    page.wait_for_timeout(1700)


def safe_click(page, selector: str, timeout: int = 8000) -> None:
    page.locator(selector).first.click(timeout=timeout)


def main() -> None:
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    if RAW_DIR.exists():
        shutil.rmtree(RAW_DIR)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    proc = ensure_dashboard()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1440, "height": 1000},
                record_video_dir=str(RAW_DIR),
                record_video_size={"width": 1440, "height": 1000},
                locale="es-CL",
            )
            page = context.new_page()
            page.on("dialog", lambda dialog: dialog.accept())
            page.goto(URL, wait_until="networkidle")
            caption(page, "Job Copilot local: dashboard de búsqueda laboral para Fabián. Nada se envía sin confirmación humana.")

            caption(page, "1) Revisa las mejores ofertas: empresa, cargo, score, canal y estado.")
            page.mouse.wheel(0, 420)
            page.wait_for_timeout(1200)
            page.mouse.wheel(0, -420)
            page.wait_for_timeout(800)

            caption(page, "2) Usa el filtro para enfocarte en una empresa u oferta concreta.")
            page.fill("#q", "Devaid")
            page.wait_for_timeout(1400)
            page.fill("#q", "")
            page.wait_for_timeout(900)

            caption(page, "3) Ejecuta un escaneo público: omite LinkedIn/login y no guarda credenciales.")
            safe_click(page, "text=Escanear fuentes públicas")
            try:
                page.wait_for_function(
                    "() => document.querySelector('#scanState')?.textContent.includes('escaneadas')",
                    timeout=45000,
                )
            except PlaywrightTimeoutError:
                pass
            page.wait_for_timeout(1200)

            caption(page, "4) Revisa razones de calce y riesgos/brechas antes de preparar una postulación.")
            page.fill("#q", "Devaid")
            page.wait_for_timeout(900)
            page.locator("article.job details summary").first.click(timeout=8000)
            page.wait_for_timeout(1300)

            caption(page, "5) Crea un paquete local: CV sugerido, correo, mensaje de formulario, checklist y postulacion.md.")
            safe_click(page, "article.job button:has-text('Crear postulación')")
            page.wait_for_timeout(1800)

            caption(page, "6) Cambia estados manualmente: revisada, requiere dato, descartada o enviada. Enviar sigue siendo decisión humana.")
            page.wait_for_timeout(1500)

            caption(page, "Listo: el tracker local se actualiza y el dashboard queda como centro seguro de postulaciones.")
            page.wait_for_timeout(2000)

            video = page.video
            context.close()
            browser.close()
            if video is None:
                raise RuntimeError("Playwright no generó video")
            raw_path = Path(video.path())
            if FINAL_WEBM.exists():
                FINAL_WEBM.unlink()
            shutil.copy2(raw_path, FINAL_WEBM)

        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg:
            subprocess.run(
                [ffmpeg, "-y", "-i", str(FINAL_WEBM), "-movflags", "+faststart", "-pix_fmt", "yuv420p", str(FINAL_MP4)],
                cwd=ROOT,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        print(f"WEBM={FINAL_WEBM}")
        print(f"MP4={FINAL_MP4 if FINAL_MP4.exists() else '[ffmpeg no disponible]'}")
    finally:
        if proc and proc.poll() is None:
            proc.terminate()


if __name__ == "__main__":
    main()
