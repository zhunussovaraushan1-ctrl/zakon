"""SQLite-хранилище. Схема переносима в PostgreSQL (списки хранятся как JSON)."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    published_at TEXT,
    raw_text TEXT,
    content_hash TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    relevance REAL,
    error TEXT,
    fetched_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(content_hash);

CREATE TABLE IF NOT EXISTS updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER REFERENCES documents(id),
    source TEXT NOT NULL,
    url TEXT NOT NULL,
    doc_title TEXT NOT NULL,
    title TEXT NOT NULL,
    doc_kind TEXT NOT NULL,
    spheres TEXT NOT NULL DEFAULT '[]',
    audience TEXT NOT NULL DEFAULT '[]',
    importance TEXT NOT NULL DEFAULT 'low',
    summary TEXT NOT NULL DEFAULT '',
    changes TEXT NOT NULL DEFAULT '[]',
    actions TEXT NOT NULL DEFAULT '[]',
    effective_date TEXT,
    published_at TEXT,
    ai_model TEXT,
    is_demo INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_updates_published ON updates(published_at);

CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    stats TEXT
);
"""

JSON_FIELDS = ("spheres", "audience", "changes", "actions")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def connect(path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def session(path: str | None = None):
    conn = connect(path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(path: str | None = None) -> None:
    with session(path) as conn:
        conn.executescript(SCHEMA)


def row_to_update(row: sqlite3.Row) -> dict:
    d = dict(row)
    for f in JSON_FIELDS:
        d[f] = json.loads(d[f] or "[]")
    d["is_demo"] = bool(d["is_demo"])
    src = config.SOURCES.get(d["source"], {})
    d["source_name"] = src.get("name", d["source"])
    d["source_official"] = src.get("official", True)
    return d


def insert_update(conn: sqlite3.Connection, upd: dict) -> int:
    data = dict(upd)
    for f in JSON_FIELDS:
        data[f] = json.dumps(data.get(f) or [], ensure_ascii=False)
    data.setdefault("created_at", now_iso())
    data["is_demo"] = int(bool(data.get("is_demo")))
    cols = [
        "document_id", "source", "url", "doc_title", "title", "doc_kind", "spheres",
        "audience", "importance", "summary", "changes", "actions", "effective_date",
        "published_at", "ai_model", "is_demo", "created_at",
    ]
    cur = conn.execute(
        f"INSERT INTO updates ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})",
        [data.get(c) for c in cols],
    )
    return cur.lastrowid


def query_updates(
    conn: sqlite3.Connection,
    sphere: str | None = None,
    audience: str | None = None,
    importance: str | None = None,
    source: str | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    where, params = [], []
    if sphere:
        where.append("EXISTS (SELECT 1 FROM json_each(updates.spheres) WHERE value = ?)")
        params.append(sphere)
    if audience:
        where.append("EXISTS (SELECT 1 FROM json_each(updates.audience) WHERE value = ?)")
        params.append(audience)
    if importance:
        where.append("importance = ?")
        params.append(importance)
    if source:
        where.append("source = ?")
        params.append(source)
    if q:
        # SQLite LOWER() не понижает кириллицу, поэтому поиск — в Python ниже
        pass
    sql_where = f"WHERE {' AND '.join(where)}" if where else ""
    order = (
        "ORDER BY CASE importance WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, "
        "COALESCE(published_at, created_at) DESC, id DESC"
    )
    rows = conn.execute(f"SELECT * FROM updates {sql_where} {order}", params).fetchall()
    items = [row_to_update(r) for r in rows]
    if q:
        needle = q.lower().strip()
        items = [u for u in items if needle in _search_blob(u)]
    total = len(items)
    return items[offset: offset + limit], total


def _search_blob(u: dict) -> str:
    parts = [u["title"], u["doc_title"], u["summary"]]
    parts += [f"{c.get('where', '')} {c.get('was', '')} {c.get('became', '')}" for c in u["changes"]]
    parts += [a.get("text", "") for a in u["actions"]]
    return " ".join(parts).lower()


def get_update(conn: sqlite3.Connection, update_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM updates WHERE id = ?", (update_id,)).fetchone()
    return row_to_update(row) if row else None


def last_run(conn: sqlite3.Connection) -> dict | None:
    row = conn.execute(
        "SELECT * FROM runs WHERE finished_at IS NOT NULL ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["stats"] = json.loads(d["stats"] or "{}")
    return d
