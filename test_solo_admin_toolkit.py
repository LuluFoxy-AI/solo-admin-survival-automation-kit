import pytest
from unittest.mock import patch

import datetime as _dt
import solo_admin_toolkit as script_under_test


def test_module_exports_and_basic_shapes():
    # Function/class existence checks
    assert hasattr(script_under_test, "SoloAdminToolkit"), "SoloAdminToolkit missing"
    assert hasattr(script_under_test, "_ts"), "_ts missing"
    assert hasattr(script_under_test, "_coerce_when"), "_coerce_when missing"
    # get_toolkit was included in __all__ in the provided module header; ensure it exists if implemented
    assert hasattr(script_under_test, "get_toolkit"), "get_toolkit missing"


def test_coerce_when_with_various_inputs():
    # datetime instance -> ISO-like string (Z suffix)
    dt = _dt.datetime(2020, 1, 2, 3, 4, 5)
    assert script_under_test._coerce_when(dt) == "2020-01-02T03:04:05Z"

    # string -> returned unchanged
    s = "someday"
    assert script_under_test._coerce_when(s) == s

    # None -> delegated to _ts; patch _ts to ensure deterministic result
    with patch.object(script_under_test, "_ts", return_value="2021-01-01T00:00:00Z"):
        assert script_under_test._coerce_when(None) == "2021-01-01T00:00:00Z"


def test_maintenance_enable_disable_and_logs_behavior():
    with patch.object(script_under_test, "_ts", return_value="TS"):
        tk = script_under_test.SoloAdminToolkit()

        # Initially disabled
        assert tk.maintenance_mode is False
        assert tk.logs == []

        # Enable once -> should flip and log once
        tk.enable_maintenance()
        assert tk.maintenance_mode is True
        assert len(tk.logs) == 1
        assert tk.logs[0] == "TS maintenance.enabled"

        # Enable again -> no duplicate log or change
        tk.enable_maintenance()
        assert tk.maintenance_mode is True
        assert len(tk.logs) == 1

        # Disable -> flips and logs
        tk.disable_maintenance()
        assert tk.maintenance_mode is False
        assert len(tk.logs) == 2
        assert tk.logs[1] == "TS maintenance.disabled"

        # set_maintenance convenience method: enabling via True
        tk.set_maintenance(True)
        assert tk.maintenance_mode is True
        assert len(tk.logs) == 3
        assert tk.logs[2] == "TS maintenance.enabled"

        # set_maintenance(False) should disable and log
        tk.set_maintenance(False)
        assert tk.maintenance_mode is False
        assert len(tk.logs) == 4
        assert tk.logs[3] == "TS maintenance.disabled"


def test_schedule_backup_dry_run_and_actual_adds_correct_job_and_logs():
    with patch.object(script_under_test, "_ts", return_value="NOW"):
        tk = script_under_test.SoloAdminToolkit()

        # Actual scheduled backup (not dry-run)
        job = tk.schedule_backup("s3://bucket/path", when=_dt.datetime(2022, 2, 2, 2, 2, 2))
        assert job["destination"] == "s3://bucket/path"
        assert job["when"] == "2022-02-02T02:02:02Z"
        assert job["label"] == "backup-1"
        assert job["created_at"] == "NOW"
        assert job["dry_run"] is False
        assert job["status"] == "scheduled"

        # It should be added to the toolkit backups list
        assert len(tk.backups) == 1
        assert tk.backups[0] is job

        # The log should contain the scheduled event and meta keys in sorted order
        # meta keys are "label" and "dest" -> sorted => dest then label
        assert len(tk.logs) >= 1
        assert tk.logs[-1] == "NOW backup.scheduled dest=s3://bucket/path label=backup-1"

        # Dry run backup: planned, not added to backups
        job2 = tk.schedule_backup("ftp://host/dir", when="tomorrow", label="nightly", dry_run=True)
        assert job2["destination"] == "ftp://host/dir"
        assert job2["when"] == "tomorrow"  # string preserved
        assert job2["label"] == "nightly"
        assert job2["created_at"] == "NOW"
        assert job2["dry_run"] is True
        assert job2["status"] == "planned"

        # No addition to backups for dry run
        assert len(tk.backups) == 1  # still only the first scheduled job

        # Log entry for planned backup
        assert tk.logs[-1] == "NOW backup.planned dest=ftp://host/dir label=nightly"


def test_add_update_behavior_and_input_validation():
    with patch.object(script_under_test, "_ts", return_value="TSTAMP"):
        tk = script_under_test.SoloAdminToolkit()

        # Adding a valid update should append and log
        tk.add_update("security-patch-1")
        assert "security-patch-1" in tk.pending_updates
        assert tk.logs[-1] == "TSTAMP update.added name=security-patch-1"

        # Adding duplicate should not duplicate entry or log again
        before_logs = list(tk.logs)
        tk.add_update("security-patch-1")
        assert tk.pending_updates.count("security-patch-1") == 1
        assert tk.logs == before_logs  # no new log entries

        # Adding falsy/empty name should be ignored
        tk.add_update("")  # should not add
        assert "" not in tk.pending_updates
        assert tk.logs == before_logs  # still unchanged


def test_log_meta_ordering_is_deterministic():
    # Ensure that when _log is called with meta containing multiple keys the keys are sorted
    with patch.object(script_under_test, "_ts", return_value="TIME"):
        tk = script_under_test.SoloAdminToolkit()
        tk._log("test.event", meta={"b": "2", "a": "1", "c": "3"})
        # Sorted keys a, b, c -> should appear in that order
        assert tk.logs[-1] == "TIME test.event a=1 b=2 c=3"