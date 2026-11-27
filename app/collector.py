"""Сбор списков документов и их текстов с сайтов-источников (F1, F2).

Соблюдает robots.txt, делает паузу между запросами, представляется понятным
User-Agent. Разметка каждого сайта берётся из config.SOURCES.
"""
from __future__ import annotations

import logging
import re
import time
from datetime import date
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from . import config

log = logging.getLogger("zanwatch.collector")

DATE_RE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")
DATE_WORDS_RE = re.compile(r"(\d{1,2})\s+([а-я]+)\s+(\d{4})", re.IGNORECASE)
MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
    "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}


def parse_date(text: str) -> str | None:
    if not text:
        return None
    m = DATE_RE.search(text)
    try:
        if m:
            return date(int(m[3]), int(m[2]), int(m[1])).isoformat()
        m = DATE_WORDS_RE.search(text)
        if m and m[2].lower() in MONTHS:
            return date(int(m[3]), MONTHS[m[2].lower()], int(m[1])).isoformat()
    except ValueError:
        return None
    return None


def parse_list(html: str, src: dict) -> list[dict]:
    """Список документов со страницы-ленты: [{url, title, published_at}]."""
    soup = BeautifulSoup(html, "lxml")
    seen: set[str] = set()
    out: list[dict] = []
    containers = soup.select(src["item_selector"]) or [soup]
    for box in containers:
        for a in box.select(src["link_selector"]):
            href = a.get("href")
            title = a.get_text(" ", strip=True)
            if not href or len(title) < 10:
                continue
            url = urljoin(src["base_url"], href).split("#")[0]
            if url in seen:
                continue
            seen.add(url)
            date_el = box.select_one(src["date_selector"]) if box is not soup else None
            published = parse_date(date_el.get_text(" ", strip=True)) if date_el else None
            out.append({"url": url, "title": title, "published_at": published or parse_date(title)})
    return out


def extract_text(html: str, src: dict) -> str:
    """Чистый текст документа: основной блок по селектору, иначе <body>."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript", "form"]):
        tag.decompose()
    node = soup.select_one(src["text_selector"]) or soup.body or soup
    for br in node.find_all("br"):
        br.replace_with("\n")
    blocks = []
    for el in node.find_all(["p", "li", "h1", "h2", "h3", "h4", "div", "td"], recursive=True):
        if el.find(["p", "li", "div", "td"]):
            continue  # берём только «листовые» блоки, чтобы не дублировать текст
        t = el.get_text(" ", strip=True)
        if t:
            blocks.append(t)
    text = "\n".join(blocks) if blocks else node.get_text("\n", strip=True)
    return re.sub(r"[ \t\xa0]+", " ", re.sub(r"\n{3,}", "\n\n", text)).strip()


class PoliteClient:
    """HTTP-клиент с robots.txt, паузой между запросами и User-Agent."""

    def __init__(self, delay: float | None = None, timeout: float = 30.0):
        self.delay = config.REQUEST_DELAY_SEC if delay is None else delay
        self.http = httpx.Client(
            headers={"User-Agent": config.USER_AGENT, "Accept-Language": "ru"},
            timeout=timeout,
            follow_redirects=True,
        )
        self._robots: dict[str, RobotFileParser | None] = {}
        self._last: dict[str, float] = {}

    def close(self) -> None:
        self.http.close()

    def allowed(self, url: str) -> bool:
        host = urlparse(url)
        key = f"{host.scheme}://{host.netloc}"
        if key not in self._robots:
            rp = RobotFileParser()
            try:
                r = self.http.get(f"{key}/robots.txt")
                if r.status_code == 200:
                    rp.parse(r.text.splitlines())
                else:
                    rp = None  # нет robots.txt — ограничений нет
            except httpx.HTTPError:
                rp = None
            self._robots[key] = rp
        rp = self._robots[key]
        return True if rp is None else rp.can_fetch(config.USER_AGENT, url)

    def get(self, url: str) -> str:
        if not self.allowed(url):
            raise PermissionError(f"robots.txt запрещает {url}")
        host = urlparse(url).netloc
        wait = self.delay - (time.monotonic() - self._last.get(host, 0))
        if wait > 0:
            time.sleep(wait)
        try:
            r = self.http.get(url)
        finally:
            self._last[host] = time.monotonic()
        r.raise_for_status()
        return r.text


def fetch_list(client: PoliteClient, source_key: str) -> list[dict]:
    src = config.SOURCES[source_key]
    html = client.get(src["list_url"])
    items = parse_list(html, src)
    log.info("%s: найдено %d ссылок", source_key, len(items))
    return items[: config.MAX_DOCS_PER_SOURCE]


def fetch_document(client: PoliteClient, source_key: str, url: str) -> str:
    return extract_text(client.get(url), config.SOURCES[source_key])
