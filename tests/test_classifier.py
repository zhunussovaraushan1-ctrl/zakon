from app.classifier import audience_for, classify, title_is_relevant


def test_title_filter():
    assert title_is_relevant("О внесении изменений в форму декларации по налогу на добавленную стоимость")
    assert title_is_relevant("Об утверждении пруденциальных нормативов страховых организаций")
    assert not title_is_relevant("О проведении республиканского конкурса юных художников")


def test_text_classification_spheres_and_roles():
    text = ("Страховые организации обязаны формировать страховые резервы. Пруденциальные нормативы "
            "страховщиков, маржа платежеспособности и требования к перестрахованию устанавливаются АРРФР.")
    ok, score, spheres = classify("Об изменении требований к страховым резервам", text)
    assert ok and score > 0
    assert spheres[0] == "insurance"
    assert audience_for(spheres) == ["insurer", "lawyer"]

    ok, _, _ = classify("О праздновании Дня города", "Провести концерт и фестиваль на площади.")
    assert not ok
