"""Отсев документов не по теме до вызова ИИ (F4) и определение сфер/ролей (F5).

Словари по сферам с весами. Первый фильтр — по заголовку (дёшево, до загрузки
текста), второй — по полному тексту.
"""
from __future__ import annotations

import re

from . import config

# Термин (основа слова, нижний регистр) → вес
KEYWORDS: dict[str, dict[str, float]] = {
    "accounting": {
        "бухгалтерск": 3, "финансовой отчетност": 3, "финансовой отчётност": 3,
        "план счетов": 3, "мсфо": 3, "нсфо": 3, "депозитарий финансовой": 3, "дфо": 2,
        "первичных документ": 2, "учетной политик": 2, "учётной политик": 2, "инвентаризац": 1,
    },
    "tax": {
        "налогов": 3, "налог ": 2, "налоге": 2, "налога": 2, "ндс": 3, "кпн": 3, "ипн": 3,
        "налоговый кодекс": 4, "эсф": 3, "счет-фактур": 3, "счёт-фактур": 3, "декларац": 2,
        "кгд": 2, "акциз": 2, "мрп": 1, "налогоплательщик": 3, "освобожден": 1,
    },
    "payroll": {
        "заработной плат": 3, "зарплат": 2, "социальн": 1, "пенсионн": 2, "опв": 3, "опвр": 3,
        "осмс": 3, "социальные отчислени": 3, "социального налога": 2, "мзп": 2,
        "минимальной заработной": 3, "трудов": 1, "енпф": 2,
    },
    "insurance": {
        "страхов": 3, "страховщик": 3, "перестрахов": 3, "огпо": 4, "пруденциальн": 3,
        "страховых резерв": 4, "актуари": 2, "страхования": 2, "аррфр": 2,
        "агентства по регулированию и развитию финансового рынка": 2, "маржа платежеспособност": 3,
    },
    "audit": {
        "аудит": 3, "аудитор": 3, "аудиторск": 3, "мса": 2, "палата аудиторов": 3,
        "внешнего аудита": 3,
    },
}

TITLE_THRESHOLD = 2.0
TEXT_THRESHOLD = 6.0


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower().replace("ё", "е"))


def score(text: str) -> dict[str, float]:
    t = _norm(text)
    result: dict[str, float] = {}
    for sphere, words in KEYWORDS.items():
        s = 0.0
        for word, weight in words.items():
            n = t.count(word.replace("ё", "е"))
            if n:
                s += weight * min(n, 5)  # не даём одному слову доминировать
        if s:
            result[sphere] = s
    return result


def title_is_relevant(title: str) -> bool:
    """Первый фильтр: заголовок. Мягкий порог — лучше пропустить на второй этап."""
    return sum(score(title).values()) >= TITLE_THRESHOLD


def classify(title: str, text: str) -> tuple[bool, float, list[str]]:
    """Второй фильтр: полный текст. Возвращает (релевантен, балл, сферы)."""
    scores = score(f"{title} {title} {text}")  # заголовок весит вдвое
    total = sum(scores.values())
    if total < TEXT_THRESHOLD:
        return False, total, []
    top = max(scores.values())
    spheres = [s for s, v in sorted(scores.items(), key=lambda x: -x[1]) if v >= top * 0.3]
    return True, total, spheres


def audience_for(spheres: list[str]) -> list[str]:
    out: list[str] = []
    for s in spheres:
        for a in config.SPHERE_AUDIENCE.get(s, []):
            if a not in out:
                out.append(a)
    return out
