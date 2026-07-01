from __future__ import annotations

import json
import re
from html import unescape
from html.parser import HTMLParser


class _VisibleTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"script", "style", "noscript", "template", "svg"}:
            self._skip_depth += 1
        if tag.lower() in {"p", "br", "li", "div", "section", "article", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style", "noscript", "template", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        if tag.lower() in {"p", "li", "div", "section", "article"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._skip_depth:
            return
        text = " ".join(unescape(data).split())
        if text:
            self.parts.append(text)


def html_to_text(value: str) -> str:
    parser = _VisibleTextParser()
    parser.feed(value or "")
    return parser.get_text() if hasattr(parser, "get_text") else _collapse(" ".join(parser.parts))


def _collapse(value: str) -> str:
    lines = [" ".join(line.split()) for line in (value or "").splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def _extract_json_description(value: str) -> str:
    # Many job boards embed a clean JobPosting.description inside script text.
    for pattern in [r'"description"\s*:\s*"((?:\\.|[^"\\])*)"', r"'description'\s*:\s*'((?:\\.|[^'\\])*)'"]:
        match = re.search(pattern, value or "", re.I | re.S)
        if not match:
            continue
        raw = match.group(1)
        try:
            decoded = json.loads(f'"{raw}"')
        except json.JSONDecodeError:
            decoded = raw.replace(r"\/", "/").replace(r"\n", "\n")
        clean = strip_html(decoded)
        if len(clean) > 120:
            return clean
    return ""


def strip_html(value: str) -> str:
    value = unescape(value or "")
    if not value.strip():
        return ""
    if "<" in value and ">" in value:
        parser = _VisibleTextParser()
        parser.feed(value)
        value = "\n".join(parser.parts)
    value = re.sub(r"<[^>]+>", " ", value)
    return _collapse(unescape(value))


def clean_job_description(value: str) -> str:
    text = value or ""
    extracted = _extract_json_description(text)
    if extracted:
        return extracted[:12000]
    text = strip_html(text)
    # Drop common JS telemetry/config blobs that leak into pages.
    noisy_prefixes = (
        "window.NREUM",
        "NREUM.info=",
        "var LANG_LOCALE",
        "var AIRA_LANGS",
        "function(",
    )
    if any(text.lstrip().startswith(prefix) for prefix in noisy_prefixes):
        # Keep the human-readable tail if one exists after obvious job markers.
        markers = ["Misión:", "Descripción:", "What you", "About the", "Responsibilities", "Requisitos", "Requirements"]
        lower = text.lower()
        best = -1
        for marker in markers:
            idx = lower.find(marker.lower())
            if idx >= 0 and (best < 0 or idx < best):
                best = idx
        text = text[best:] if best >= 0 else ""
    text = re.sub(r"\b(window|document)\.[A-Za-z0-9_.$(){};:=,\"'\[\]-]{40,}", " ", text)
    return _collapse(text)[:12000]
