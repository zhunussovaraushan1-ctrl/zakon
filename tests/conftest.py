import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest


@pytest.fixture()
def tmp_db(tmp_path, monkeypatch):
    from app import config
    path = str(tmp_path / "test.db")
    monkeypatch.setattr(config, "DB_PATH", path)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    return path
