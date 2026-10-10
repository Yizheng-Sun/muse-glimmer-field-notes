"""Tests for honest usage extraction and lossless evaluation reporting."""
from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from eval_metrics import extract_attempt_metrics, extract_session_metrics, write_reports


class SessionMetricsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "session.jsonl"

    def write(self, session):
        self.path.write_text(json.dumps(session), encoding="utf-8")
        return extract_session_metrics(self.path)

    def test_real_c02_export_counts_calls_once_and_includes_cached_input_once(self):
        path = ROOT / ".runs/coding/C02/analysis/20261010_184903_fe2ff8/session.jsonl"
        if not path.exists():
            self.skipTest("Optional owner-provided C02 export is not present in this checkout")
        metrics = extract_session_metrics(path)
        self.assertEqual(metrics["session_id"], "20261010_184903_fe2ff8")
        self.assertEqual(metrics["metrics_scope"], "main_agent_session")
        self.assertEqual(metrics["assistant_turns"], 61)
        self.assertEqual(metrics["tool_iterations"], 60)
        self.assertEqual(metrics["tool_calls"], 60)
        self.assertEqual(metrics["user_messages"], 2)
        self.assertEqual(metrics["api_calls"], 60)
        self.assertEqual(metrics["input_tokens"], 27395)
        self.assertEqual(metrics["output_tokens"], 20992)
        self.assertEqual(metrics["uncached_input_output_tokens"], 48387)
        self.assertEqual(metrics["prompt_tokens"], 1398966)
        self.assertEqual(metrics["total_tokens"], 1419958)
        self.assertEqual(metrics["cache_read_tokens"], 1371571)
        self.assertAlmostEqual(metrics["session_elapsed_seconds"], 331.8336399, places=4)
        self.assertTrue(any("reported as zero" in warning for warning in metrics["metrics_warnings"]))

    def test_missing_usage_remains_null(self):
        metrics = self.write({"id": "minimal", "messages": []})
        for name in ("input_tokens", "output_tokens", "prompt_tokens", "total_tokens", "uncached_input_output_tokens", "reasoning_tokens", "cache_read_tokens", "cache_write_tokens", "api_calls"):
            self.assertIsNone(metrics[name])
        self.assertEqual(metrics["tool_calls"], 0)
        self.assertEqual(metrics["assistant_turns"], 0)
        self.assertIsNone(metrics["session_elapsed_seconds"])

    def test_reported_zero_is_preserved_without_claiming_reasoning_disabled(self):
        metrics = self.write({"id": "zero", "input_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0, "cache_read_tokens": 0, "cache_write_tokens": 0, "api_call_count": 0, "tool_call_count": 0, "messages": []})
        self.assertEqual(metrics["total_tokens"], 0)
        self.assertEqual(metrics["reasoning_tokens"], 0)
        self.assertTrue(any("does not establish" in warning for warning in metrics["metrics_warnings"]))

    def test_canonical_total_adds_cache_details_once_and_not_reasoning_again(self):
        metrics = self.write({"id": "canonical", "input_tokens": 10, "cache_read_tokens": 100, "cache_write_tokens": 7, "output_tokens": 30, "reasoning_tokens": 20, "messages": []})
        self.assertEqual(metrics["prompt_tokens"], 117)
        self.assertEqual(metrics["total_tokens"], 147)
        self.assertEqual(metrics["uncached_input_output_tokens"], 40)
        self.assertEqual(metrics["reasoning_tokens"], 20)
        metrics = self.write({"id": "partial", "input_tokens": 10, "cache_read_tokens": 100, "output_tokens": 30, "messages": []})
        self.assertIsNone(metrics["prompt_tokens"])
        self.assertIsNone(metrics["total_tokens"])
        self.assertEqual(metrics["uncached_input_output_tokens"], 40)

    def test_inactive_work_is_retained_and_parallel_tools_count_as_one_iteration(self):
        metrics = self.write({"id": "rewound", "tool_call_count": 3, "messages": [
            {"role": "user", "active": 1},
            {"role": "assistant", "active": 0, "observed": 1, "tool_calls": [{"id": "a"}, {"id": "b"}]},
            {"role": "tool", "active": 0},
            {"role": "assistant", "active": 1, "tool_calls": json.dumps([{"id": "c"}])},
            {"role": "assistant", "active": 1, "content": "Done"},
        ]})
        self.assertEqual(metrics["tool_calls"], 3)
        self.assertEqual(metrics["tool_iterations"], 2)
        self.assertEqual(metrics["assistant_turns"], 3)
        self.assertEqual(metrics["inactive_tool_calls"], 2)
        self.assertEqual(metrics["active_tool_calls"], 1)
        self.assertEqual(metrics["inactive_assistant_turns"], 1)
        self.assertEqual(metrics["active_assistant_turns"], 2)
        self.assertEqual(metrics["observed_message_count"], 1)
        self.assertTrue(any("inactive/rewound" in warning for warning in metrics["metrics_warnings"]))

    def test_jsonl_selects_session_and_latest_snapshot_without_adding_usage(self):
        self.path.write_text("\n".join(json.dumps(item) for item in [
            {"id": "a", "input_tokens": 4, "output_tokens": 3, "messages": []},
            {"id": "b", "input_tokens": 8, "output_tokens": 7, "messages": []},
            {"id": "a", "input_tokens": 9, "output_tokens": 6, "messages": []},
        ]), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "multiple sessions"):
            extract_session_metrics(self.path)
        self.assertEqual(extract_session_metrics(self.path, "a")["uncached_input_output_tokens"], 15)
        self.assertIsNone(extract_session_metrics(self.path, "a")["total_tokens"])
        with self.assertRaisesRegex(ValueError, "was not found"):
            extract_session_metrics(self.path, "missing")

    def test_iso_timestamps_and_invalid_tokens_are_not_estimated(self):
        metrics = self.write({"id": "iso", "started_at": "2026-10-10T18:49:06Z", "ended_at": "2026-10-10T18:49:08+00:00", "input_tokens": 9, "output_tokens": 2.5, "reasoning_tokens": True, "messages": []})
        self.assertEqual(metrics["session_elapsed_seconds"], 2)
        self.assertIsNone(metrics["output_tokens"])
        self.assertIsNone(metrics["reasoning_tokens"])
        self.assertIsNone(metrics["total_tokens"])
        metrics = self.write({"id": "naive", "started_at": "2026-10-10T18:49:06", "ended_at": "2026-10-10T18:49:08", "messages": []})
        self.assertIsNone(metrics["session_elapsed_seconds"])

    def test_malformed_messages_do_not_produce_zero_counts(self):
        metrics = self.write({"id": "malformed", "messages": "missing"})
        self.assertIsNone(metrics["assistant_turns"])
        metrics = self.write({"id": "bad-tools", "messages": [{"role": "assistant", "tool_calls": "not-json"}]})
        self.assertEqual(metrics["assistant_turns"], 1)
        self.assertIsNone(metrics["tool_calls"])
        self.assertIsNone(metrics["tool_iterations"])


class AttemptMetricsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.source = self.folder / "source"
        self.source.mkdir()
        self.export = self.folder / "sessions.jsonl"
        self.db = self.folder / "state.db"

    def session(self, identity, parent=None, messages=None, **values):
        return {"id": identity, "parent_session_id": parent, "cwd": str(self.source), "started_at": 10, "ended_at": 20, "api_call_count": 4, "tool_call_count": 3, "input_tokens": 999, "output_tokens": 888, "cache_read_tokens": 777, "cache_write_tokens": 666, "reasoning_tokens": 555, "messages": messages or [], **values}

    def write_export(self, sessions):
        self.export.write_text("\n".join(json.dumps(session) for session in sessions), encoding="utf-8")

    def write_usage(self, rows):
        with sqlite3.connect(self.db) as connection:
            connection.execute("CREATE TABLE session_model_usage (session_id TEXT, task TEXT, api_call_count INTEGER, input_tokens INTEGER, output_tokens INTEGER, cache_read_tokens INTEGER, cache_write_tokens INTEGER, reasoning_tokens INTEGER)")
            connection.executemany("INSERT INTO session_model_usage VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)

    def test_compressed_history_uses_occurrence_uids_and_additive_database_usage(self):
        shared = {"role": "assistant", "message_uid": "shared-message", "active": 0, "tool_calls": [{"id": "reused"}], "tool_call_uids": json.dumps({"reused": "first-occurrence"})}
        later = {"role": "assistant", "message_uid": "later-message", "active": 1, "tool_calls": [{"id": "reused"}, {"id": "reused"}], "tool_call_uids": {"reused": ["second-occurrence", "third-occurrence"]}}
        root = self.session("root", messages=[shared], ended_at=14, api_call_count=2)
        child = self.session("child", "root", messages=[{**shared, "active": 1}, later], started_at=14, ended_at=25)
        self.write_export([root, child])
        self.write_usage([("root", "", 2, 10, 20, 30, 0, 8), ("child", "", 1, 2, 3, 4, 5, 1), ("child", "helper", 9, 1000, 1000, 1000, 1000, 1000)])
        original_db = self.db.read_bytes()
        metrics = extract_attempt_metrics(self.export, self.source, self.db)
        self.assertEqual(metrics["metrics_scope"], "main_agent_attempt")
        self.assertEqual(metrics["session_ids"], ["root", "child"])
        self.assertEqual(metrics["session_id"], "child")
        self.assertEqual(metrics["assistant_turns"], 2)
        self.assertEqual(metrics["tool_iterations"], 2)
        self.assertEqual(metrics["tool_calls"], 3)
        self.assertEqual(metrics["active_tool_calls"], 3)
        self.assertEqual(metrics["input_tokens"], 12)
        self.assertEqual(metrics["output_tokens"], 23)
        self.assertEqual(metrics["prompt_tokens"], 51)
        self.assertEqual(metrics["total_tokens"], 74)
        self.assertEqual(metrics["reasoning_tokens"], 9)
        self.assertEqual(metrics["api_calls"], 4)
        self.assertEqual(metrics["api_calls_with_usage"], 3)
        self.assertEqual(metrics["session_elapsed_seconds"], 15)
        self.assertTrue(any("fewer API calls" in warning for warning in metrics["metrics_warnings"]))
        self.assertEqual(self.db.read_bytes(), original_db)

    def test_latest_snapshot_and_selected_session_api_counter_are_not_added(self):
        root = self.session("root", api_call_count=9)
        child = self.session("child", "root", api_call_count=4)
        newer_child = {**child, "api_call_count": 7}
        self.write_export([root, child, newer_child])
        metrics = extract_attempt_metrics(self.export, self.source, session_id="child")
        self.assertEqual(metrics["api_calls"], 7)
        self.assertEqual(metrics["session_ids"], ["root", "child"])
        self.assertIsNone(metrics["total_tokens"])
        self.assertEqual(extract_attempt_metrics(self.export, self.source)["api_calls"], 9)

    def test_single_session_native_fallback_is_supported(self):
        self.write_export([self.session("root")])
        metrics = extract_attempt_metrics(self.export, self.source)
        self.assertEqual(metrics["total_tokens"], 3330)
        self.assertEqual(metrics["usage_source"], "native_session_export")
        self.assertIsNone(metrics["api_calls_with_usage"])

    def test_missing_uid_in_compressed_history_makes_work_counts_unknown(self):
        self.write_export([self.session("root", messages=[{"role": "assistant"}]), self.session("child", "root")])
        metrics = extract_attempt_metrics(self.export, self.source)
        self.assertIsNone(metrics["assistant_turns"])
        self.assertIsNone(metrics["tool_calls"])
        self.assertIsNone(metrics["total_tokens"])
        self.assertTrue(any("missing message occurrence UIDs" in warning for warning in metrics["metrics_warnings"]))
        self.write_export([self.session("root", messages=[{"role": "assistant", "message_uid": "message", "tool_calls": [{"id": "provider"}]}]), self.session("child", "root")])
        metrics = extract_attempt_metrics(self.export, self.source)
        self.assertIsNone(metrics["tool_calls"])
        self.assertTrue(any("missing tool occurrence UIDs" in warning for warning in metrics["metrics_warnings"]))

    def test_unrelated_missing_parent_and_cwd_mismatch_are_rejected(self):
        for sessions in ([self.session("a"), self.session("b")], [self.session("a"), self.session("b", "missing")], [self.session("a"), self.session("b", "c"), self.session("c", "b")], [self.session("a", cwd=str(self.folder / "other"))]):
            with self.subTest(sessions=sessions):
                self.write_export(sessions)
                with self.assertRaises(ValueError):
                    extract_attempt_metrics(self.export, self.source)

    def test_missing_main_database_rows_keep_multi_session_tokens_unknown(self):
        self.write_export([self.session("root"), self.session("child", "root")])
        self.write_usage([("child", "helper", 1, 100, 100, 100, 0, 10)])
        metrics = extract_attempt_metrics(self.export, self.source, self.db)
        self.assertIsNone(metrics["total_tokens"])
        self.assertIsNone(metrics["api_calls_with_usage"])
        self.assertTrue(any("no main-agent usage" in warning for warning in metrics["metrics_warnings"]))

    def test_unexported_main_usage_is_not_mixed_into_attempt(self):
        self.write_export([self.session("root"), self.session("child", "root")])
        self.write_usage([("other", "", 1, 100, 100, 100, 0, 10)])
        metrics = extract_attempt_metrics(self.export, self.source, self.db)
        self.assertIsNone(metrics["total_tokens"])
        self.assertTrue(any("outside the validated export lineage" in warning for warning in metrics["metrics_warnings"]))


class ReportingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.batch = Path(self.temporary.name)

    def result(self, run_id, **values):
        path = self.batch / "runs" / run_id / "result.json"
        path.parent.mkdir(parents=True)
        record = {"run_id": run_id, "case_id": "C02", "budget_name": "short", "reasoning_effort": "low", "max_turns": 10, "max_seconds": 60, **values}
        path.write_text(json.dumps(record), encoding="utf-8")
        return record

    def test_reports_keep_functional_results_separate_from_process_status(self):
        passed = self.result("pass", verdict="PASS", process_status="budget_exhausted", elapsed_seconds=5, metrics={"total_tokens": 100, "tool_iterations": 10}, unknown_field={"keep": True})
        failed = self.result("fail", verdict="FAIL", process_status="completed", elapsed_seconds=3, metrics={"total_tokens": None, "tool_iterations": 2})
        error = self.result("infra", verdict="UNKNOWN", process_status="setup_error", error="Missing interpreter")
        skipped = self.result("skip", verdict="SKIPPED", process_status="reasoning_unsupported", reasoning_effort="xhigh", error="Effort unavailable")
        write_reports(self.batch)
        records = [json.loads(line) for line in (self.batch / "results.jsonl").read_text().splitlines()]
        self.assertCountEqual(records, [passed, failed, error, skipped])
        with (self.batch / "results.csv").open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        pass_row = next(row for row in rows if row["run_id"] == "pass")
        self.assertEqual(pass_row["verdict"], "PASS")
        self.assertEqual(pass_row["process_status"], "budget_exhausted")
        self.assertEqual(pass_row["total_tokens"], "100")
        self.assertEqual(json.loads(pass_row["unknown_field"]), {"keep": True})
        self.assertEqual(next(row for row in rows if row["run_id"] == "fail")["total_tokens"], "")
        summary = (self.batch / "summary.md").read_text()
        self.assertIn("50.0% (1/2)", summary)
        self.assertIn("100 (1/3 recorded)", summary)
        self.assertIn("| setup_error | 1 |", summary)
        self.assertIn("| UNKNOWN | 1 |", summary)
        self.assertIn("| SKIPPED | 1 |", summary)
        self.assertIn("Missing interpreter", summary)
        self.assertIn("xhigh", summary)

    def test_archived_attempts_are_preserved_alongside_fresh_retries(self):
        current = self.result("same-job", verdict="PASS", process_status="completed", auxiliary_input_tokens=12, auxiliary_output_tokens=3, auxiliary_usage={"scope": "helper", "recorded": True})
        archived = {**current, "verdict": "UNKNOWN", "process_status": "interrupted", "error": "Interrupted during model execution", "archive_marker": "original attempt"}
        path = self.batch / "incomplete" / "same-job-20261010T120000Z" / "result.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(archived), encoding="utf-8")
        write_reports(self.batch)
        records = [json.loads(line) for line in (self.batch / "results.jsonl").read_text().splitlines()]
        self.assertCountEqual(records, [archived, current])
        self.assertEqual(len(records), 2)
        with (self.batch / "results.csv").open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 2)
        current_row = next(row for row in rows if row["verdict"] == "PASS")
        self.assertEqual(current_row["auxiliary_input_tokens"], "12")
        self.assertEqual(json.loads(current_row["auxiliary_usage"]), current["auxiliary_usage"])
        summary = (self.batch / "summary.md").read_text()
        self.assertIn("Attempts recorded: **2**", summary)
        self.assertIn("| interrupted | 1 |", summary)
        self.assertIn("| UNKNOWN | 1 |", summary)
        self.assertIn("Auxiliary-task usage is preserved separately", summary)

    def test_invalid_result_is_visible_and_empty_batch_is_reportable(self):
        write_reports(self.batch)
        self.assertEqual((self.batch / "results.jsonl").read_text(), "")
        self.assertIn("No run results", (self.batch / "summary.md").read_text())
        path = self.batch / "runs" / "broken" / "result.json"
        path.parent.mkdir(parents=True)
        path.write_text("partial{", encoding="utf-8")
        write_reports(self.batch)
        record = json.loads((self.batch / "results.jsonl").read_text())
        self.assertEqual(record["verdict"], "UNKNOWN")
        self.assertEqual(record["process_status"], "report_error")
        self.assertIn("Cannot read", record["error"])


if __name__ == "__main__":
    unittest.main()
