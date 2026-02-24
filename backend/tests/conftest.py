from __future__ import annotations

from pathlib import Path

import pytest

from app.db.sqlite import repository
from app.rag.retriever import retriever
from app.services import settings
from app.services.medgemma import medgemma_client


@pytest.fixture(autouse=True)
def _test_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "astra_test.db"
    repository.db_path = db_path
    repository.init_db()

    monkeypatch.setattr(settings, "MEDGEMMA_RUNTIME", "mock", raising=False)
    monkeypatch.setattr(settings, "ASTRA_FAIL_AFTER_NODE", None, raising=False)
    monkeypatch.setattr(settings, "ENFORCE_ALEMBIC_HEAD", True, raising=False)
    monkeypatch.setattr(settings, "AUTO_RESUME_INCOMPLETE_RUNS", False, raising=False)

    medgemma_client.runtime = "mock"
    medgemma_client.model = "mock-model"
    retriever._collection = None
