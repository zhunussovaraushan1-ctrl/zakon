"""Собирает автономную демо-версию интерфейса (без сервера) в dist/zanwatch-demo.html.

Данные — 7 демо-карточек из app/demo.py, встроенные прямо в страницу; запросы к API
подменяются чтением этих данных. Нужна, чтобы показать интерфейс по ссылке.

    python tools/build_static_demo.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import config, demo  # noqa: E402


def demo_data() -> tuple[list[dict], dict]:
    items = []
    for i, u in enumerate(demo.demo_updates(), start=1):
        src = config.SOURCES[u["source"]]
        items.append({**u, "id": i, "document_id": None, "ai_model": "demo", "is_demo": True,
                      "source_name": src["name"], "source_official": src["official"]})
    meta = {
        "spheres": config.SPHERES,
        "audiences": config.AUDIENCES,
        "sources": {k: {"name": v["name"], "kind": v["kind"], "official": v["official"]}
                    for k, v in config.SOURCES.items()},
        "last_collect": None,
        "demo": True,
    }
    return items, meta


FAKE_API = """const DEMO_ITEMS = __ITEMS__;
const DEMO_META = __META__;
// Демо-версия без сервера: API отвечает встроенными данными
async function api(path){
  const url = new URL(path, "https://demo.local");
  if(url.pathname === "/api/meta") return DEMO_META;
  const m = url.pathname.match(/^\\/api\\/updates\\/(\\d+)$/);
  if(m){ const u = DEMO_ITEMS.find(x => x.id === Number(m[1])); if(!u) throw new Error(404); return u; }
  const aud = url.searchParams.get("audience");
  const rank = {high:0, medium:1, low:2};
  const items = DEMO_ITEMS.filter(u => !aud || u.audience.includes(aud))
    .sort((a, b) => rank[a.importance] - rank[b.importance] || (b.published_at || "").localeCompare(a.published_at || ""));
  return {items, total: items.length, limit: 200, offset: 0};
}"""


def build() -> Path:
    html = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
    items, meta = demo_data()

    # Обёртку документа добавляет хостинг; убираем свою и PWA-ссылки
    for pat in [r"<!doctype html>\s*", r"<html[^>]*>\s*", r"</?head>\s*", r"</?body>\s*", r"</html>\s*",
                r'<meta charset[^>]*>\s*', r'<meta name="viewport"[^>]*>\s*',
                r'<link rel="(?:manifest|icon|apple-touch-icon)"[^>]*>\s*']:
        html = re.sub(pat, "", html, flags=re.IGNORECASE)
    html = html.replace("<title>ZanWatch</title>",
                        '<title>ZanWatch</title>\n<meta name="claude:viewport-fit-sides" content="cover">', 1)

    api_re = re.compile(r"async function api\(path\)\{.*?\n\}", re.DOTALL)
    assert api_re.search(html), "не найдена функция api()"
    fake = (FAKE_API.replace("__ITEMS__", json.dumps(items, ensure_ascii=False))
            .replace("__META__", json.dumps(meta, ensure_ascii=False)))
    html = api_re.sub(lambda _: fake, html, count=1)

    html = re.sub(r'\s*if\("serviceWorker" in navigator\)[^\n]*', "", html)

    out = ROOT / "dist" / "zanwatch-demo.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out


if __name__ == "__main__":
    print(build())
