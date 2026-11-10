import os
import sqlite3
from pathlib import Path

import pytest

from app.audit_log import record_event
from app.secure_storage import prepare_private_sqlite


def test_sqlite_storage_uses_private_directory_and_file_modes(tmp_path):
    path = prepare_private_sqlite(tmp_path / "private" / "state.sqlite3")
    assert path.exists()
    assert os.stat(path.parent).st_mode & 0o777 == 0o700
    assert os.stat(path).st_mode & 0o777 == 0o600
    path.chmod(0o644)
    prepare_private_sqlite(path)
    assert os.stat(path).st_mode & 0o777 == 0o600


def test_audit_log_is_allowlisted_redacted_and_bounded(monkeypatch, tmp_path):
    path = tmp_path / "audit" / "events.sqlite3"
    monkeypatch.setenv("AMR_AUDIT_DB_PATH", str(path))
    resource_id = "7e4aa784-75e3-48fc-b366-5ef14466f771"
    assert record_event("auth.login", "failure")
    assert record_event("publishing.state", "scheduled", resource_id)
    with sqlite3.connect(path) as db:
        rows = db.execute("SELECT event, outcome, resource_id FROM audit_events ORDER BY id").fetchall()
        assert rows == [("auth.login", "failure", None), ("publishing.state", "scheduled", resource_id)]
        dump = " ".join(map(str, rows))
        assert "password" not in dump and "token" not in dump and "caption" not in dump
    with pytest.raises(ValueError):
        record_event("auth.login", "password=secret")
    with pytest.raises(ValueError):
        record_event("publishing.state", "scheduled", "caption-containing-private-data")


def test_sqlite_symlink_is_refused(tmp_path):
    target = tmp_path / "target.sqlite3"
    target.touch()
    link = tmp_path / "link.sqlite3"
    link.symlink_to(target)
    with pytest.raises(OSError):
        prepare_private_sqlite(link)
