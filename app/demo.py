"""7 демо-карточек для показа формата. Помечены is_demo=1 (U12).

Содержание вымышлено и служит только для показа интерфейса — это не реальные нормы.
Отключается настройкой ZW_SEED_DEMO=0.
"""
from __future__ import annotations

from datetime import date, timedelta

from . import db


def _d(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def demo_updates() -> list[dict]:
    return [
        {
            "source": "adilet", "url": "https://adilet.zan.kz/rus/index/docs/dt=new",
            "doc_title": "[Демо] Приказ Министра финансов РК о внесении изменений в форму декларации по корпоративному подоходному налогу",
            "title": "Обновлена форма декларации по КПН (ф. 100.00)",
            "doc_kind": "npa", "spheres": ["tax", "accounting"], "audience": ["accountant", "lawyer"],
            "importance": "high",
            "summary": "В декларацию по КПН добавлено новое приложение для расходов на цифровые активы, изменена строка корректировки дохода. Новая форма применяется к отчётности за текущий год.",
            "changes": [
                {"where": "Форма 100.00, строка 100.00.012", "was": "Доход от прироста стоимости", "became": "Доход от прироста стоимости, включая цифровые активы"},
                {"where": "Форма 100.00, приложение 100.08", "was": "", "became": "Новое приложение «Расходы по цифровым активам»"},
            ],
            "actions": [
                {"text": "Обновить шаблон декларации в учётной системе", "deadline": _d(10), "who": "accountant"},
                {"text": "Собрать данные по операциям с цифровыми активами", "deadline": _d(30), "who": "accountant"},
            ],
            "effective_date": _d(10), "published_at": _d(-2),
        },
        {
            "source": "ardfm", "url": "https://www.gov.kz/memleket/entities/ardfm",
            "doc_title": "[Демо] Постановление Правления АРРФР о внесении изменений в нормативные значения пруденциальных нормативов страховых организаций",
            "title": "Повышен норматив маржи платёжеспособности страховщиков",
            "doc_kind": "npa", "spheres": ["insurance"], "audience": ["insurer", "lawyer"],
            "importance": "high",
            "summary": "Минимальное значение норматива маржи платёжеспособности повышено. Страховым организациям нужно пересчитать норматив и при необходимости увеличить капитал до даты вступления в силу.",
            "changes": [
                {"where": "Пункт 5 Нормативных значений", "was": "не менее 1", "became": "не менее 1,1"},
            ],
            "actions": [
                {"text": "Пересчитать маржу платёжеспособности по новой формуле", "deadline": _d(7), "who": "insurer"},
                {"text": "Подготовить план докапитализации при дефиците", "deadline": _d(45), "who": "insurer"},
            ],
            "effective_date": _d(60), "published_at": _d(-1),
        },
        {
            "source": "minfin", "url": "https://www.gov.kz/memleket/entities/minfin",
            "doc_title": "[Демо] Приказ МФ РК о внесении изменений в Типовой план счетов бухгалтерского учёта",
            "title": "В Типовой план счетов добавлены субсчета для аренды",
            "doc_kind": "npa", "spheres": ["accounting"], "audience": ["accountant"],
            "importance": "medium",
            "summary": "В раздел долгосрочных обязательств добавлены отдельные счета для обязательств по аренде. Компаниям нужно обновить рабочий план счетов.",
            "changes": [
                {"where": "Раздел 4, подраздел 4400", "was": "", "became": "Счёт 4430 «Долгосрочные обязательства по аренде»"},
            ],
            "actions": [
                {"text": "Добавить новые счета в рабочий план счетов", "deadline": _d(25), "who": "accountant"},
            ],
            "effective_date": _d(25), "published_at": _d(-4),
        },
        {
            "source": "kgd", "url": "https://kgd.gov.kz/ru/news",
            "doc_title": "[Демо] Разъяснение КГД по выписке ЭСФ при возврате товаров",
            "title": "КГД разъяснил порядок исправленных ЭСФ при возврате",
            "doc_kind": "explanation", "spheres": ["tax"], "audience": ["accountant", "lawyer"],
            "importance": "low",
            "summary": "При возврате товара выписывается дополнительный, а не исправленный ЭСФ. Новых обязанностей разъяснение не вводит.",
            "changes": [], "actions": [], "effective_date": None, "published_at": _d(-3),
        },
        {
            "source": "adilet", "url": "https://adilet.zan.kz/rus/index/docs/dt=new",
            "doc_title": "[Демо] Постановление Правительства РК об изменении ставок обязательных пенсионных взносов работодателя",
            "title": "ОПВР: изменена ставка с 1 января",
            "doc_kind": "npa", "spheres": ["payroll"], "audience": ["accountant"],
            "importance": "high",
            "summary": "Ставка обязательных пенсионных взносов работодателя меняется с 1 января. Нужно обновить настройки расчёта зарплаты.",
            "changes": [
                {"where": "Пункт 1", "was": "2,5 % от дохода работника", "became": "3,5 % от дохода работника"},
            ],
            "actions": [
                {"text": "Обновить ставку ОПВР в зарплатной программе", "deadline": _d(20), "who": "accountant"},
                {"text": "Пересчитать бюджет ФОТ на следующий год", "deadline": _d(14), "who": "accountant"},
            ],
            "effective_date": _d(35), "published_at": _d(-5),
        },
        {
            "source": "uchet", "url": "https://uchet.kz/news/",
            "doc_title": "[Демо] Обзор: что изменится в аудите с нового года",
            "title": "Обзор изменений в требованиях к аудиторским отчётам",
            "doc_kind": "news", "spheres": ["audit"], "audience": ["accountant"],
            "importance": "medium",
            "summary": "Обзор новых требований к раскрытию ключевых вопросов аудита. Это неофициальный источник — сверяйтесь с текстом НПА.",
            "changes": [],
            "actions": [
                {"text": "Сверить требования с текстом НПА на adilet.zan.kz", "deadline": "", "who": "accountant"},
            ],
            "effective_date": None, "published_at": _d(-6),
        },
        {
            "source": "ardfm", "url": "https://www.gov.kz/memleket/entities/ardfm",
            "doc_title": "[Демо] Постановление АРРФР о внесении изменений в правила ОГПО владельцев транспортных средств",
            "title": "ОГПО ВТС: новый порядок урегулирования убытков",
            "doc_kind": "npa", "spheres": ["insurance"], "audience": ["insurer", "lawyer"],
            "importance": "medium",
            "summary": "Срок рассмотрения заявления о страховой выплате по ОГПО ВТС сокращён, добавлена возможность подачи через электронный сервис.",
            "changes": [
                {"where": "Пункт 12 Правил", "was": "в течение 15 рабочих дней", "became": "в течение 10 рабочих дней"},
            ],
            "actions": [
                {"text": "Обновить внутренний регламент урегулирования убытков", "deadline": _d(40), "who": "insurer"},
                {"text": "Проверить договоры с аварийными комиссарами", "deadline": _d(40), "who": "lawyer"},
            ],
            "effective_date": _d(40), "published_at": _d(-7),
        },
    ]


def seed(conn) -> int:
    if conn.execute("SELECT 1 FROM updates WHERE is_demo = 1 LIMIT 1").fetchone():
        return 0
    for u in demo_updates():
        db.insert_update(conn, {**u, "document_id": None, "ai_model": "demo", "is_demo": True})
    return 7


def remove(conn) -> None:
    conn.execute("DELETE FROM updates WHERE is_demo = 1")
