"""Настройки приложения и разметка сайтов-источников.

Если вёрстка сайта изменится, правится только SOURCES — код трогать не нужно.
Адреса лент и CSS-селекторы заданы по типовой вёрстке и требуют сверки
перед первым боевым сбором (см. PRD, раздел 11).
"""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.getenv("ZW_DB_PATH", str(BASE_DIR.parent / "zanwatch.db"))

ADMIN_TOKEN = os.getenv("ZW_ADMIN_TOKEN", "change-me")
LLM_MODEL = os.getenv("ZW_LLM_MODEL", "claude-opus-5-5")
SEED_DEMO = os.getenv("ZW_SEED_DEMO", "1") != "0"
COLLECT_INTERVAL_HOURS = float(os.getenv("ZW_COLLECT_INTERVAL_HOURS", "0"))  # 0 = не запускать по расписанию
REQUEST_DELAY_SEC = float(os.getenv("ZW_REQUEST_DELAY_SEC", "2"))
MAX_DOCS_PER_SOURCE = int(os.getenv("ZW_MAX_DOCS_PER_SOURCE", "30"))
USER_AGENT = os.getenv(
    "ZW_USER_AGENT",
    "ZanWatchBot/0.1 (+monitoring of RK accounting/tax/insurance legislation)",
)

SPHERES = {
    "accounting": "Бухучёт",
    "tax": "Налоги",
    "payroll": "Зарплата и взносы",
    "insurance": "Страхование",
    "audit": "Аудит",
}

AUDIENCES = {
    "accountant": "Бухгалтер",
    "lawyer": "Юрист",
    "insurer": "Страховщик",
}

# Сопоставление «сфера → роли» (PRD, раздел 3)
SPHERE_AUDIENCE = {
    "accounting": ["accountant"],
    "tax": ["accountant", "lawyer"],
    "payroll": ["accountant"],
    "insurance": ["insurer", "lawyer"],
    "audit": ["accountant"],
}

# kind: npa | explanation | news; official: официальный источник или «Обзор»
SOURCES = {
    "adilet": {
        "name": "Әділет (adilet.zan.kz)",
        "kind": "npa",
        "official": True,
        "list_url": "https://adilet.zan.kz/rus/index/docs/dt=new",
        "item_selector": "div.post_holder, div.serp li, ul.result li",
        "link_selector": "a[href*='/rus/docs/']",
        "date_selector": ".date, .post_date",
        "text_selector": "div.container_gamma, div#text, div.text",
        "base_url": "https://adilet.zan.kz",
    },
    "ardfm": {
        "name": "АРРФР",
        "kind": "npa",
        "official": True,
        "list_url": "https://www.gov.kz/memleket/entities/ardfm/documents/1?lang=ru",
        "item_selector": "div.document-item, li.documents__item, a.card",
        "link_selector": "a[href*='/documents/details/']",
        "date_selector": ".date, time",
        "text_selector": "div.document-content, div.content, article",
        "base_url": "https://www.gov.kz",
    },
    "minfin": {
        "name": "Минфин РК",
        "kind": "npa",
        "official": True,
        "list_url": "https://www.gov.kz/memleket/entities/minfin/documents/1?lang=ru",
        "item_selector": "div.document-item, li.documents__item, a.card",
        "link_selector": "a[href*='/documents/details/']",
        "date_selector": ".date, time",
        "text_selector": "div.document-content, div.content, article",
        "base_url": "https://www.gov.kz",
    },
    "kgd": {
        "name": "КГД МФ РК",
        "kind": "explanation",
        "official": True,
        "list_url": "https://kgd.gov.kz/ru/news",
        "item_selector": "div.views-row, article",
        "link_selector": "a[href*='/ru/']",
        "date_selector": ".date-display-single, time",
        "text_selector": "div.field-name-body, div.content, article",
        "base_url": "https://kgd.gov.kz",
    },
    "uchet": {
        "name": "uchet.kz",
        "kind": "news",
        "official": False,
        "list_url": "https://uchet.kz/news/",
        "item_selector": "div.news-item, article",
        "link_selector": "a[href*='/news/']",
        "date_selector": ".date, time",
        "text_selector": "div.news-detail, div.article-body, article",
        "base_url": "https://uchet.kz",
    },
    "zan": {
        "name": "zan.kz",
        "kind": "news",
        "official": False,
        "list_url": "https://zan.kz/ru/list/news",
        "item_selector": "div.news-item, article",
        "link_selector": "a[href*='/ru/']",
        "date_selector": ".date, time",
        "text_selector": "div.article-body, div.content, article",
        "base_url": "https://zan.kz",
    },
}
