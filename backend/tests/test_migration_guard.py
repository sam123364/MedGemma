from __future__ import annotations

from pathlib import Path

import pytest

from app.db.sqlite import repository
from app.main import startup
from app.services import settings


@pytest.mark.asyncio
async def test_startup_fails_when_alembic_revision_is_behind(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repository.db_path = tmp_path / "migration_guard.db"
    repository.init_db()
    repository.set_alembic_revision("20240101_old")

    monkeypatch.setattr(settings, "ENFORCE_ALEMBIC_HEAD", True, raising=False)
    monkeypatch.setattr(settings, "ALEMBIC_HEAD_REVISION", "20260224_0001", raising=False)

    with pytest.raises(RuntimeError):
        await startup()

