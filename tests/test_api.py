from fastapi.testclient import TestClient


def test_api_feed_filters_and_card(tmp_db, monkeypatch):
    from app import config, main
    monkeypatch.setattr(config, "SEED_DEMO", True)
    monkeypatch.setattr(config, "ADMIN_TOKEN", "secret")
    monkeypatch.setattr(main.pipeline, "run", lambda *a, **k: {})

    with TestClient(main.app) as client:
        r = client.get("/api/updates")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 7
        assert all(u["is_demo"] for u in data["items"])
        # сверху — важные
        imps = [u["importance"] for u in data["items"]]
        assert imps == sorted(imps, key={"high": 0, "medium": 1, "low": 2}.get)

        ins = client.get("/api/updates", params={"audience": "insurer"}).json()["items"]
        assert ins and all("insurer" in u["audience"] for u in ins)
        tax = client.get("/api/updates", params={"sphere": "tax"}).json()["items"]
        assert tax and all("tax" in u["spheres"] for u in tax)
        found = client.get("/api/updates", params={"q": "ОПВР"}).json()["items"]
        assert len(found) == 1

        card = client.get(f"/api/updates/{found[0]['id']}").json()
        assert card["changes"] and card["actions"] and card["url"].startswith("https://")
        assert client.get("/api/updates/99999").status_code == 404

        meta = client.get("/api/meta").json()
        assert set(meta["spheres"]) == {"accounting", "tax", "payroll", "insurance", "audit"}
        assert set(meta["audiences"]) == {"accountant", "lawyer", "insurer"}

        assert client.post("/api/collect").status_code == 401
        assert client.post("/api/collect", headers={"X-Admin-Token": "wrong"}).status_code == 401
        assert client.post("/api/collect", headers={"X-Admin-Token": "secret"}).status_code == 202
        assert client.get("/").status_code == 200


def test_pipeline_offline_rules(tmp_db, monkeypatch):
    """Конвейер без сети и без ИИ: сводка по правилам, повторный документ не обрабатывается."""
    from app import collector, db, pipeline

    html_list = '<div class="post_holder"><a href="/rus/docs/V1">О внесении изменений в Налоговый кодекс по ставкам НДС</a><span class="date">25.11.2026</span></div>'
    doc_text = ("Внести в Налоговый кодекс следующие изменения: 1) в пункте 1 статьи 422 слова «12 процентов» "
                "заменить словами «16 процентов»; Налогоплательщики НДС применяют новую ставку налога. "
                "Настоящий Закон вводится в действие с 1 января 2027 года.")

    class FakeClient:
        def __init__(self, *a, **k): pass
        def get(self, url): return html_list
        def close(self): pass

    monkeypatch.setattr(collector, "PoliteClient", FakeClient)
    monkeypatch.setattr(collector, "fetch_document", lambda c, s, u: doc_text)

    stats = pipeline.run(["adilet"])
    assert stats["processed"] == 1 and stats["rules"] == 1, stats
    with db.session() as conn:
        items, total = db.query_updates(conn)
    u = items[0]
    assert {"where": "в пункте 1 статьи 422", "was": "12 процентов", "became": "16 процентов"} in u["changes"]
    assert u["effective_date"] == "2027-01-01"
    assert u["importance"] == "high" and u["ai_model"] == "rules"
    assert "tax" in u["spheres"]

    stats2 = pipeline.run(["adilet"])
    assert stats2["seen"] == 1 and stats2["processed"] == 0
