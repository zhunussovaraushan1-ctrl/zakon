from app import config
from app.collector import extract_text, parse_list

LIST_HTML = """
<html><body>
<div class="post_holder">
  <a href="/rus/docs/V2600012345">О внесении изменений в Типовой план счетов бухгалтерского учета</a>
  <span class="date">20.11.2026</span>
</div>
<div class="post_holder">
  <a href="/rus/docs/V2600012399">Об утверждении формы налоговой декларации по КПН</a>
  <span class="date">21 ноября 2026</span>
</div>
<div class="post_holder"><a href="/rus/docs/short">Кратко</a></div>
</body></html>
"""

DOC_HTML = """
<html><head><script>var x=1;</script></head><body>
<nav>Меню сайта</nav>
<div class="container_gamma">
  <h1>Приказ Министра финансов</h1>
  <p>1) в пункте 3 слова «А» заменить словами «Б»;</p>
  <p>Настоящий приказ вводится в действие с 1 января 2027 года.</p>
</div>
<footer>Подвал</footer>
</body></html>
"""


def test_parse_list():
    items = parse_list(LIST_HTML, config.SOURCES["adilet"])
    assert len(items) == 2
    assert items[0]["url"] == "https://adilet.zan.kz/rus/docs/V2600012345"
    assert items[0]["published_at"] == "2026-11-20"
    assert items[1]["published_at"] == "2026-11-21"


def test_extract_text():
    text = extract_text(DOC_HTML, config.SOURCES["adilet"])
    assert "заменить словами «Б»" in text
    assert "вводится в действие" in text
    assert "Меню сайта" not in text and "var x" not in text and "Подвал" not in text
