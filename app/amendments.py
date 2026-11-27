"""Извлечение «было/стало» из актов «о внесении изменений» без ИИ (F6)
и даты вступления в силу (F7).

Шаблоны: «заменить», «изложить в следующей редакции», «дополнить», «исключить».
"""
from __future__ import annotations

import re
from datetime import date

Q = r"[«\"“]"      # открывающая кавычка
QE = r"[»\"”]"     # закрывающая кавычка

# Где применяется правка: «в пункте 3 статьи 12», «подпункт 2) пункта 1 статьи 5», «статью 7»
WHERE_RE = re.compile(
    r"((?:в\s+)?(?:абзаце?|абзац|подпункте?|подпункт|части|часть|пункте?|пункт|статье|статью|статья|главе|главу|приложении|приложение)"
    r"[^:;«\"]{0,120}?)\s*(?=:|слов|цифр|изложить|дополнить|исключить)",
    re.IGNORECASE,
)

REPLACE_RE = re.compile(
    rf"(?:слова?|цифры?|знаки?)\s+{Q}(?P<was>.+?){QE}\s+заменить\s+(?:словами|словом|цифрами|цифрой|знаками)\s+{Q}(?P<became>.+?){QE}",
    re.IGNORECASE | re.DOTALL,
)
REDACTION_RE = re.compile(
    rf"изложить\s+в\s+(?:следующей|новой)\s+редакции\s*:\s*{Q}(?P<became>.+?){QE}\s*[;.]",
    re.IGNORECASE | re.DOTALL,
)
ADD_RE = re.compile(
    rf"дополнить\s+(?P<what>[^:]{{0,120}}?)\s*(?:следующего\s+содержания)?\s*:\s*{Q}(?P<became>.+?){QE}\s*[;.]",
    re.IGNORECASE | re.DOTALL,
)
ADD_WORDS_RE = re.compile(
    rf"дополнить\s+словами\s+{Q}(?P<became>.+?){QE}",
    re.IGNORECASE | re.DOTALL,
)
EXCLUDE_WORDS_RE = re.compile(
    rf"слова?\s+{Q}(?P<was>.+?){QE}\s+исключить",
    re.IGNORECASE | re.DOTALL,
)
EXCLUDE_RE = re.compile(
    r"(?P<where>(?:абзац|подпункт|пункт|часть|статью|главу)[^;:.«]{0,80}?)\s+исключить",
    re.IGNORECASE,
)

MAX_LEN = 600


def _clean(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= MAX_LEN else s[: MAX_LEN - 1] + "…"


def _split_items(text: str) -> list[str]:
    """Режем текст на подпункты правок «1) …; 2) …» / «1. …». Строки-продолжения
    (например, новая редакция в кавычках на следующей строке) приклеиваются к своему подпункту."""
    parts = re.split(r"\n+(?=\s*\d{1,3}[).]\s)|(?<=;)\s+(?=\d{1,3}\)\s)", text)
    parts = [p.replace("\n", " ") for p in parts]
    return [p for p in (x.strip() for x in parts) if p]


def extract_changes(text: str, limit: int = 30) -> list[dict]:
    changes: list[dict] = []
    current_where = ""
    for item in _split_items(text):
        m_where = WHERE_RE.search(item)
        if m_where:
            current_where = _clean(m_where.group(1))
        found = False
        for m in REPLACE_RE.finditer(item):
            changes.append({"where": current_where, "was": _clean(m["was"]), "became": _clean(m["became"])})
            found = True
        if not found:
            m = REDACTION_RE.search(item)
            if m:
                changes.append({"where": current_where, "was": "(прежняя редакция)", "became": _clean(m["became"])})
                found = True
        if not found:
            m = ADD_WORDS_RE.search(item)
            if m:
                changes.append({"where": current_where, "was": "", "became": _clean(m["became"])})
                found = True
        if not found:
            m = ADD_RE.search(item)
            if m:
                where = current_where or _clean(m["what"])
                changes.append({"where": where, "was": "", "became": _clean(m["became"])})
                found = True
        if not found:
            m = EXCLUDE_WORDS_RE.search(item)
            if m:
                changes.append({"where": current_where, "was": _clean(m["was"]), "became": "(исключено)"})
                found = True
        if not found:
            m = EXCLUDE_RE.search(item)
            if m:
                changes.append({"where": _clean(m["where"]), "was": "(действующая норма)", "became": "(исключено)"})
        if len(changes) >= limit:
            break
    return changes


MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
    "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}

EFFECTIVE_RE = re.compile(
    r"(?:вводится|вводятся)\s+в\s+действие\s+с\s+(?P<d>\d{1,2})\s+(?P<m>[а-я]+)\s+(?P<y>\d{4})"
    r"|(?:вступает|вступают)\s+в\s+силу\s+с\s+(?P<d2>\d{1,2})\s+(?P<m2>[а-я]+)\s+(?P<y2>\d{4})"
    r"|(?:вводится|вводятся)\s+в\s+действие\s+с\s+(?P<d3>\d{2})\.(?P<m3>\d{2})\.(?P<y3>\d{4})",
    re.IGNORECASE,
)


def extract_effective_date(text: str) -> str | None:
    """Самая ранняя дата из фраз «вводится в действие / вступает в силу с …»."""
    dates: list[date] = []
    for m in EFFECTIVE_RE.finditer(text or ""):
        try:
            if m["d"]:
                dates.append(date(int(m["y"]), MONTHS[m["m"].lower()], int(m["d"])))
            elif m["d2"]:
                dates.append(date(int(m["y2"]), MONTHS[m["m2"].lower()], int(m["d2"])))
            elif m["d3"]:
                dates.append(date(int(m["y3"]), int(m["m3"]), int(m["d3"])))
        except (KeyError, ValueError):
            continue
    return min(dates).isoformat() if dates else None


def is_amendment_act(title: str) -> bool:
    return bool(re.search(r"о\s+внесении\s+(?:изменений|изменения|дополнений)", title or "", re.IGNORECASE))
