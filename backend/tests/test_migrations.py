"""Migration tests against a populated database (SQLite table rebuilds must keep data and FKs)."""

import sqlite3
import uuid
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command

BACKEND_DIR = Path(__file__).resolve().parents[1]
NOW = "2026-10-28 09:00:00.000000"


def alembic_config() -> Config:
    # No ini file: avoids fileConfig() reconfiguring logging for the rest of the test session.
    config = Config()
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return config


def test_visitor_snapshot_migration_backfills_existing_visits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "migrate.db"
    monkeypatch.setenv("VMP_DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    config = alembic_config()
    command.upgrade(config, "1618e688acc0")

    user_id, visitor_id, visit_id = (uuid.uuid4().hex for _ in range(3))
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("a@acme-corp.com", "Alice", "x", "EMPLOYEE", 1, user_id, NOW, NOW),
        )
        conn.execute(
            "INSERT INTO visitors VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("Jane Doe", "jane@contoso.com", "+33 1", "Contoso", visitor_id, NOW, NOW),
        )
        conn.execute(
            "INSERT INTO visits (visitor_id, host_id, registered_by_id, purpose, expected_date,"
            " status, id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (visitor_id, user_id, user_id, "Review", "2026-10-28", "EXPECTED", visit_id, NOW, NOW),
        )
        # A row referencing `visits` forces the table rebuild to cope with foreign keys.
        conn.execute(
            "INSERT INTO audit_logs (visit_id, action, to_status, performed_by_id, occurred_at, id)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (visit_id, "VISIT_CREATED", "EXPECTED", user_id, NOW, uuid.uuid4().hex),
        )

    command.upgrade(config, "head")

    with sqlite3.connect(db_path) as conn:
        snapshot = conn.execute(
            "SELECT visitor_full_name, visitor_phone, visitor_company FROM visits"
        ).fetchall()
        audit_rows = conn.execute("SELECT count(*) FROM audit_logs").fetchone()
        not_null = {row[1]: row[3] for row in conn.execute("PRAGMA table_info(visits)")}
    assert snapshot == [("Jane Doe", "+33 1", "Contoso")]
    assert audit_rows == (1,)
    assert not_null["visitor_full_name"] == 1
    assert not_null["visitor_company"] == 1
    assert not_null["visitor_phone"] == 0

    command.downgrade(config, "1618e688acc0")
