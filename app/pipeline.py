"""Конвейер: источники → список → фильтр по заголовку → текст → фильтр по тексту
→ разбор правок → ИИ-сводка → SQLite.

Запуск вручную: python -m app.pipeline [--source adilet]
Сбой одного источника или ИИ не останавливает конвейер; ошибки пишутся в runs.stats.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import threading

from . import amendments, classifier, collector, config, db, summarizer

log = logging.getLogger("zanwatch.pipeline")
_lock = threading.Lock()


def _process_document(conn, source_key: str, doc_id: int, title: str, url: str,
                      published_at: str | None, text: str, stats: dict) -> None:
    src = config.SOURCES[source_key]
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    dup = conn.execute(
        "SELECT id FROM documents WHERE content_hash = ? AND id != ?", (content_hash, doc_id)
    ).fetchone()
    if dup:  # F3: тот же текст под другим URL
        conn.execute("UPDATE documents SET raw_text=?, content_hash=?, status='irrelevant', error='дубликат' WHERE id=?",
                     (text, content_hash, doc_id))
        stats["duplicates"] += 1
        return

    relevant, relevance, spheres = classifier.classify(title, text)
    conn.execute("UPDATE documents SET raw_text=?, content_hash=?, relevance=?, status=? WHERE id=?",
                 (text, content_hash, relevance, "relevant" if relevant else "irrelevant", doc_id))
    if not relevant:
        stats["irrelevant_text"] += 1
        return

    hint_changes = amendments.extract_changes(text) if amendments.is_amendment_act(title) or src["kind"] == "npa" else []
    effective = amendments.extract_effective_date(text)
    s = summarizer.summarize(title, text, src["name"], spheres, hint_changes, effective)
    db.insert_update(conn, {
        "document_id": doc_id,
        "source": source_key,
        "url": url,
        "doc_title": title,
        "title": s["title"],
        "doc_kind": src["kind"],
        "spheres": spheres,
        "audience": classifier.audience_for(spheres),
        "importance": s["importance"],
        "summary": s["summary"],
        "changes": s["changes"],
        "actions": s["actions"],
        "effective_date": s["effective_date"],
        "published_at": published_at,
        "ai_model": s["ai_model"],
        "is_demo": False,
    })
    conn.execute("UPDATE documents SET status='processed' WHERE id=?", (doc_id,))
    stats["processed"] += 1
    stats["ai" if s["ai_model"] != "rules" else "rules"] += 1


def run_source(conn, client: collector.PoliteClient, source_key: str, stats: dict) -> None:
    items = collector.fetch_list(client, source_key)
    for item in items:
        stats["listed"] += 1
        if conn.execute("SELECT 1 FROM documents WHERE url = ?", (item["url"],)).fetchone():
            stats["seen"] += 1  # F3: уже обрабатывали
            continue
        title_ok = classifier.title_is_relevant(item["title"])
        cur = conn.execute(
            "INSERT INTO documents (source, url, title, published_at, status, fetched_at) VALUES (?,?,?,?,?,?)",
            (source_key, item["url"], item["title"], item["published_at"],
             "new" if title_ok else "irrelevant", db.now_iso()),
        )
        doc_id = cur.lastrowid
        conn.commit()
        if not title_ok:
            stats["irrelevant_title"] += 1
            continue
        try:
            text = collector.fetch_document(client, source_key, item["url"])
            _process_document(conn, source_key, doc_id, item["title"], item["url"],
                              item["published_at"], text, stats)
        except Exception as e:
            log.exception("Документ %s: ошибка", item["url"])
            conn.execute("UPDATE documents SET status='error', error=? WHERE id=?", (str(e)[:500], doc_id))
            stats["errors"].append({"source": source_key, "url": item["url"], "error": str(e)[:300]})
        conn.commit()


def run(sources: list[str] | None = None) -> dict:
    """Один проход сбора. Возвращает статистику (она же пишется в runs)."""
    if not _lock.acquire(blocking=False):
        return {"skipped": "сбор уже идёт"}
    try:
        db.init_db()
        stats = {"listed": 0, "seen": 0, "irrelevant_title": 0, "irrelevant_text": 0, "duplicates": 0,
                 "processed": 0, "ai": 0, "rules": 0, "errors": [], "failed_sources": []}
        with db.session() as conn:
            run_id = conn.execute("INSERT INTO runs (started_at) VALUES (?)", (db.now_iso(),)).lastrowid
            conn.commit()
            client = collector.PoliteClient()
            try:
                for key in sources or list(config.SOURCES):
                    try:
                        run_source(conn, client, key, stats)
                    except Exception as e:
                        log.warning("Источник %s недоступен: %s", key, e)
                        stats["failed_sources"].append({"source": key, "error": str(e)[:300]})
            finally:
                client.close()
            conn.execute("UPDATE runs SET finished_at=?, stats=? WHERE id=?",
                         (db.now_iso(), json.dumps(stats, ensure_ascii=False), run_id))
        return stats
    finally:
        _lock.release()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(description="ZanWatch: ручной сбор")
    p.add_argument("--source", action="append", choices=list(config.SOURCES), help="только этот источник")
    args = p.parse_args()
    print(json.dumps(run(args.source), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
