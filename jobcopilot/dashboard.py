from __future__ import annotations
import json
import mimetypes
import threading
import time
import webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
from .storage import ROOT, load_jobs, save_jobs, load_config
from .models import Job
from .scoring import score_job
from .package import create_package
from .scanner import SOURCES_PATH, load_last_scan, run_scan

DATA = ROOT / "data"
WEB = ROOT / "web"
SOURCES = SOURCES_PATH
SAFE_STATUSES = {"new", "reviewed", "prepared", "sent", "discarded", "requires_info"}


def read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class Handler(BaseHTTPRequestHandler):
    def _send(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def _json(self, data, status=200):
        self._send(status)
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def log_message(self, format, *args):
        return

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            path = WEB / "index.html"
            self._send(200, "text/html; charset=utf-8")
            self.wfile.write(path.read_bytes())
            return
        if parsed.path == "/api/jobs":
            self._json([j.to_dict() for j in sorted(load_jobs(), key=lambda x: (x.status == "discarded", -x.score))])
            return
        if parsed.path == "/api/sources":
            self._json(read_json(SOURCES, {"searches": [], "target_companies": [], "company_links": []}))
            return
        if parsed.path == "/api/config":
            c = load_config()
            safe = {
                "candidate": c.get("candidate", {}),
                "keywords": c.get("must_have_keywords", []),
                "avoid": c.get("avoid_keywords", []),
                "automation": c.get("automation", {}),
            }
            self._json(safe)
            return
        if parsed.path == "/api/scan":
            self._json(load_last_scan())
            return
        if parsed.path.startswith("/exports/"):
            path = ROOT / parsed.path.lstrip("/")
            if path.exists() and path.is_file() and ROOT in path.resolve().parents:
                ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                self._send(200, ctype)
                self.wfile.write(path.read_bytes())
                return
        self._json({"error": "not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            data = json.loads(body or "{}")
        except json.JSONDecodeError:
            return self._json({"error": "invalid json"}, 400)

        if parsed.path == "/api/jobs":
            jobs = load_jobs()
            next_id = max([j.id for j in jobs], default=0) + 1
            job = Job(
                id=next_id,
                company=data.get("company") or "[COMPLETAR EMPRESA]",
                role=data.get("role") or "[COMPLETAR CARGO]",
                url=data.get("url") or "[COMPLETAR URL]",
                source=data.get("source") or "dashboard",
                location=data.get("location") or "Chile / remoto",
                description=data.get("description") or "",
                status="new",
            )
            job = score_job(job, load_config())
            jobs.append(job)
            save_jobs(jobs)
            return self._json(job.to_dict(), 201)

        if parsed.path == "/api/score":
            config = load_config()
            jobs = [score_job(j, config) for j in load_jobs()]
            save_jobs(jobs)
            return self._json({"ok": True, "count": len(jobs)})

        if parsed.path == "/api/scan":
            result = run_scan()
            return self._json(result)

        if parsed.path == "/api/package":
            job_id = int(data.get("id", 0))
            jobs = load_jobs()
            job = next((j for j in jobs if j.id == job_id), None)
            if not job:
                return self._json({"error": "job not found"}, 404)
            if not job.score:
                job = score_job(job, load_config())
            folder = create_package(job, load_config(), ROOT)
            job.status = "prepared"
            save_jobs(jobs)
            return self._json({"ok": True, "folder": str(folder), "relative": str(folder.relative_to(ROOT)).replace(chr(92), "/")})

        if parsed.path == "/api/status":
            job_id = int(data.get("id", 0))
            status = data.get("status") or "reviewed"
            if status not in SAFE_STATUSES:
                return self._json({"error": "invalid status"}, 400)
            jobs = load_jobs()
            for job in jobs:
                if job.id == job_id:
                    job.status = status
                    save_jobs(jobs)
                    return self._json(job.to_dict())
            return self._json({"error": "job not found"}, 404)

        self._json({"error": "not found"}, 404)


def _auto_scan_loop(interval_minutes: int):
    interval_seconds = max(5, interval_minutes * 60)
    while True:
        try:
            run_scan()
        except Exception as exc:
            print(f"[auto-scan] error: {exc}")
        time.sleep(interval_seconds)


def serve(host="127.0.0.1", port=8765, open_browser=True):
    config = load_config()
    interval = int(config.get("automation", {}).get("auto_scan_minutes", 0) or 0)
    if interval > 0:
        threading.Thread(target=_auto_scan_loop, args=(interval,), daemon=True).start()
        print(f"Auto-scan público cada {interval} min (sin credenciales, sin enviar postulaciones).")
    server = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{port}"
    print(f"Dashboard: {url}")
    if open_browser:
        webbrowser.open(url)
    server.serve_forever()
