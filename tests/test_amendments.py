from app.amendments import extract_changes, extract_effective_date, is_amendment_act

AMENDMENT_TEXT = """
1. Внести в приказ Министра финансов Республики Казахстан следующие изменения:
1) в пункте 3 статьи 12 слова «до 15 марта» заменить словами «до 31 марта»;
2) пункт 5 изложить в следующей редакции:
«5. Ставка составляет 12 процентов.»;
3) статью 7 дополнить пунктом 4 следующего содержания:
«4. Отчётность представляется в электронной форме.»;
4) подпункт 2) пункта 8 исключить;
2. Настоящий приказ вводится в действие с 1 января 2027 года, за исключением подпункта 3), который вступает в силу с 15 декабря 2026 года.
"""


def test_extract_changes_patterns():
    changes = extract_changes(AMENDMENT_TEXT)
    assert {"where": "в пункте 3 статьи 12", "was": "до 15 марта", "became": "до 31 марта"} in changes
    redaction = [c for c in changes if c["became"].startswith("5. Ставка")]
    assert redaction and redaction[0]["where"].startswith("пункт 5")
    added = [c for c in changes if "электронной форме" in c["became"]]
    assert added and added[0]["was"] == ""
    excluded = [c for c in changes if c["became"] == "(исключено)"]
    assert excluded and "пункта 8" in excluded[0]["where"]


def test_effective_date_and_title():
    assert extract_effective_date(AMENDMENT_TEXT) == "2026-12-15"  # самая ранняя
    assert extract_effective_date("Без даты") is None
    assert is_amendment_act("О внесении изменений в приказ Министра финансов")
    assert not is_amendment_act("Об утверждении Правил")
