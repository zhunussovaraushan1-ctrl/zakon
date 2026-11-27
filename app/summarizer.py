"""Сводка по документу: суть, «было → стало», действия, сроки, важность (F8–F10).

Основной путь — Claude API со структурированным ответом по JSON-схеме.
Правки, найденные правилами (amendments.py), передаются ИИ как подсказка.
Если ключа нет или вызов не удался — сводка строится по правилам.
"""
from __future__ import annotations

import json
import logging
import os
import re

from . import config

log = logging.getLogger("zanwatch.summarizer")

MAX_INPUT_CHARS = 120_000  # ~1/4 контекста; длинные кодексы режем с явной пометкой

SYSTEM_PROMPT = """Ты — аналитик законодательства Республики Казахстан в сферах бухгалтерского учёта, \
налогов, зарплаты и взносов, страхования и аудита. Твои читатели — бухгалтеры, юристы и специалисты \
страховых компаний. Им не нужно читать весь документ: они хотят за минуту понять, что изменилось и что делать.

Правила достоверности (важнее всего остального):
- Пиши только то, что прямо следует из текста документа. Не додумывай нормы, ставки, сроки, номера статей.
- Если данных нет — оставь поле пустым (пустая строка или пустой список). Пустое поле лучше выдуманного.
- Правки из подсказки «найдено правилами» проверь по тексту; используй, если они подтверждаются.
- Даты пиши в формате ГГГГ-ММ-ДД.

Поля ответа:
- title: понятный заголовок до 90 символов, без канцелярита («Новая форма декларации по КПН с 2027 года»).
- summary: суть в 2–3 предложениях простым языком.
- changes: конкретные правки — where (статья/пункт), was (было), became (стало). Для новых норм was пустой.
- actions: что сделать читателю — text (действие), deadline (ГГГГ-ММ-ДД или пусто), who (accountant | lawyer | insurer).
- importance: high — меняются ставки, сроки, формы отчётности, штрафы, требования к капиталу или резервам; \
medium — процедурные изменения; low — уточнения и разъяснения без новых обязанностей.
- effective_date: дата вступления в силу (ГГГГ-ММ-ДД) или пусто.
Пиши по-русски."""

SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string"},
        "changes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "where": {"type": "string"},
                    "was": {"type": "string"},
                    "became": {"type": "string"},
                },
                "required": ["where", "was", "became"],
                "additionalProperties": False,
            },
        },
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "deadline": {"type": "string"},
                    "who": {"type": "string", "enum": ["accountant", "lawyer", "insurer"]},
                },
                "required": ["text", "deadline", "who"],
                "additionalProperties": False,
            },
        },
        "importance": {"type": "string", "enum": ["high", "medium", "low"]},
        "effective_date": {"type": "string"},
    },
    "required": ["title", "summary", "changes", "actions", "importance", "effective_date"],
    "additionalProperties": False,
}

DATE_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HIGH_WORDS = ("ставк", "срок", "форм", "штраф", "капитал", "резерв", "норматив", "размер", "процент")


def _validate(data: dict, fallback_effective: str | None) -> dict:
    """Проверка ответа по схеме (F10): лишнее отбрасываем, кривые даты обнуляем."""
    if not isinstance(data, dict):
        raise ValueError("ответ не объект")
    out = {
        "title": str(data.get("title", "")).strip()[:140],
        "summary": str(data.get("summary", "")).strip(),
        "importance": data.get("importance") if data.get("importance") in ("high", "medium", "low") else "medium",
        "changes": [],
        "actions": [],
    }
    for c in data.get("changes") or []:
        if isinstance(c, dict) and (c.get("became") or c.get("was")):
            out["changes"].append({k: str(c.get(k, "")).strip() for k in ("where", "was", "became")})
    for a in data.get("actions") or []:
        if isinstance(a, dict) and a.get("text"):
            dl = str(a.get("deadline", "")).strip()
            who = a.get("who") if a.get("who") in config.AUDIENCES else "accountant"
            out["actions"].append({"text": str(a["text"]).strip(), "deadline": dl if DATE_ISO.match(dl) else "", "who": who})
    eff = str(data.get("effective_date", "")).strip()
    out["effective_date"] = eff if DATE_ISO.match(eff) else fallback_effective
    if not out["title"] or not out["summary"]:
        raise ValueError("пустой заголовок или суть")
    return out


def rule_based(title: str, text: str, spheres: list[str], changes: list[dict], effective_date: str | None) -> dict:
    """Сводка без ИИ (F9): первые предложения текста + правки по правилам."""
    sentences = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text or "").strip())
    body = [s for s in sentences if len(s) > 40 and not s.lower().startswith(("примечание", "сноска"))]
    summary = " ".join(body[:2])[:500] or title
    blob = " ".join(f"{c['was']} {c['became']}" for c in changes).lower() + " " + title.lower()
    if changes and any(w in blob for w in HIGH_WORDS):
        importance = "high"
    elif changes:
        importance = "medium"
    else:
        importance = "low"
    who = {"insurance": "insurer"}.get(spheres[0] if spheres else "", "accountant")
    actions = []
    if changes:
        actions.append({
            "text": "Изучить правки и обновить внутренние документы и процессы",
            "deadline": effective_date or "",
            "who": who,
        })
    return {
        "title": title[:140],
        "summary": summary,
        "changes": changes,
        "actions": actions,
        "importance": importance,
        "effective_date": effective_date,
        "ai_model": "rules",
    }


def _llm_available() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))


def llm_summary(title: str, text: str, source_name: str, spheres: list[str],
                hint_changes: list[dict], effective_date: str | None) -> dict:
    import anthropic

    truncated = len(text) > MAX_INPUT_CHARS
    body = text[:MAX_INPUT_CHARS]
    open_tag = '<document truncated="true">' if truncated else "<document>"
    hints = json.dumps(hint_changes, ensure_ascii=False, indent=1) if hint_changes else "нет"
    user = (
        f"Источник: {source_name}\n"
        f"Официальное название: {title}\n"
        f"Сферы (по классификатору): {', '.join(spheres) or 'не определены'}\n"
        f"Дата вступления в силу (найдено правилами): {effective_date or 'не найдена'}\n"
        f"Правки (найдено правилами, проверь по тексту):\n"
        f"{hints}\n\n"
        f"{open_tag}\n{body}\n</document>"
    )
    client = anthropic.Anthropic()
    response = client.beta.messages.create(
        model=config.LLM_MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": user}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("модель отказалась обрабатывать документ")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("ответ обрезан по max_tokens")
    raw = "".join(b.text for b in response.content if b.type == "text")
    result = _validate(json.loads(raw), effective_date)
    result["ai_model"] = response.model
    return result


def summarize(title: str, text: str, source_name: str, spheres: list[str],
              hint_changes: list[dict], effective_date: str | None) -> dict:
    if _llm_available():
        try:
            return llm_summary(title, text, source_name, spheres, hint_changes, effective_date)
        except Exception as e:  # сбой ИИ не останавливает конвейер (раздел 9, «Надёжность»)
            log.warning("ИИ-сводка не удалась (%s), строим по правилам", e)
    return rule_based(title, text, spheres, hint_changes, effective_date)
