from __future__ import annotations
from html.parser import HTMLParser
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self._in_title = False
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data):
        text = " ".join(data.split())
        if not text:
            return
        if self._in_title:
            self.title += text + " "
        if len(text) > 2:
            self.parts.append(text)


def fetch_url_text(url: str, timeout: int = 20) -> tuple[str, str]:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 JobApplicationCopilot/0.1"})
    try:
        with urlopen(req, timeout=timeout) as res:
            raw = res.read(1_500_000)
            content_type = res.headers.get("content-type", "")
    except (HTTPError, URLError, TimeoutError) as exc:
        return "", f"[NO SE PUDO EXTRAER: {exc}]"
    encoding = "utf-8"
    if "charset=" in content_type:
        encoding = content_type.split("charset=", 1)[1].split(";", 1)[0].strip()
    html = raw.decode(encoding, errors="replace")
    parser = TextExtractor()
    parser.feed(html)
    text = "\n".join(parser.parts)
    return parser.title.strip(), text[:12000]
