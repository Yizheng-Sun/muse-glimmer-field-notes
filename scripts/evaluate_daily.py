#!/usr/bin/env python3
"""Run and grade synthetic daily tasks through the installed Hermes agent."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import itertools
import json
import os
from pathlib import Path
import platform
import random
import shutil
import subprocess
import sys
import threading
import time
from urllib.parse import unquote, urlsplit

import evaluate_coding as core
from daily_cases import CATALOG, VARIANTS
from daily_checks import expand, safe_file
from eval_metrics import METRIC_FIELDS, extract_attempt_metrics, write_reports

ROOT = Path(__file__).resolve().parents[1]
CASE_IDS = [row[0] for row in CATALOG]
FROZEN_SCRIPTS = ("evaluate_daily.py", "daily_cases.py", "daily_checks.py", "evaluate_coding.py", "eval_metrics.py")


def validate_config(config, case_dir=None):
    if config.get("provider", "glimmer") != "glimmer":
        raise ValueError("Daily evaluation currently uses the loopback Glimmer provider")
    for field, allowed in (("cases", CASE_IDS), ("variants", VARIANTS)):
        values = config.get(field)
        if not isinstance(values, list) or not values or any(x not in allowed for x in values) or len(values) != len(set(values)):
            raise ValueError(f"{field} must select unique values from {', '.join(allowed)}")
    # Reuse the existing backend, sampling, budget and credential validation.
    # Coding dependency pins are validation-only defaults, never installed here.
    core.validate_config({**config, "cases": ["C01"], "pytest_version": "9.0.2", "flit_core_version": "3.12.0"})
    max_phases = max(len(read_case(case, case_dir)["variants"][v]["phases"]) for case in config["cases"] for v in config["variants"])
    if any(b["max_turns"] < max_phases for b in config["budgets"]):
        raise ValueError("Each budget needs at least one iteration per task phase")
    return config


def read_case(case_id, directory=None):
    case = json.loads(((directory or ROOT / "cases/daily") / f"{case_id}.json").read_text())
    if case.get("case_id") != case_id or case.get("schema_version") != 1:
        raise ValueError(f"Invalid daily case definition: {case_id}")
    for variant in VARIANTS:
        data = case["variants"][variant]
        if not data["phases"] or not data["checks"]:
            raise ValueError(f"Missing phases/checks: {case_id}/{variant}")
        for name in data["files"]:
            safe_file(ROOT / ".runs/validation", name)
        for p in data["phases"]:
            if not isinstance(p["prompt"], str) or not p["prompt"].strip():
                raise ValueError("Every phase needs a prompt")
            if any(name not in data["files"] for name in p.get("remove_before", [])):
                raise ValueError("Removed phase inputs must be named fixture files")
            if any(name not in data["files"] for name in p.get("provide_before", [])):
                raise ValueError("Provided phase inputs must be named fixture files")
        if any(name not in data["files"] for name in data["mutable_inputs"]):
            raise ValueError("Mutable inputs must be named fixture files")
    return case


def make_jobs(config):
    jobs = []
    for case, variant, budget, effort, repeat in itertools.product(config["cases"], config["variants"], config["budgets"], config["reasoning_efforts"], range(1, config["repeats"] + 1)):
        jobs.append({"run_id": f"{case}-{variant}-{budget['name']}-{effort}-r{repeat:02d}", "case_id": case,
                     "variant": variant, "budget_name": budget["name"], "reasoning_effort": effort,
                     "repeat": repeat, "max_turns": budget["max_turns"], "max_seconds": budget["max_seconds"]})
    random.Random(config.get("shuffle_seed", 42)).shuffle(jobs)
    return jobs


def current_scripts():
    return {name: core.digest(ROOT / "scripts" / name) for name in FROZEN_SCRIPTS}


def freeze_batch(config, batch):
    (batch / "inputs").mkdir()
    manifests = {}
    for case_id in config["cases"]:
        read_case(case_id)
        target = batch / "inputs" / f"{case_id}.json"
        shutil.copyfile(ROOT / "cases/daily" / f"{case_id}.json", target)
        manifests[case_id] = core.digest(target)
    (batch / "tools").mkdir()
    shutil.copyfile(ROOT / "scripts/daily_checks.py", batch / "tools/daily_checks.py")
    core.save_json(batch / "config.json", config)
    core.save_json(batch / "jobs.json", make_jobs(config))
    try:
        commit = core.git("rev-parse", "HEAD")
        dirty = bool(core.git("status", "--porcelain"))
    except (OSError, subprocess.SubprocessError):
        commit, dirty = None, None
    core.save_json(batch / "manifest.json", {"cases": manifests, "scripts": current_scripts(),
                    "checker_sha256": core.digest(batch / "tools/daily_checks.py"),
                    "config_sha256": core.digest(batch / "config.json"), "jobs_sha256": core.digest(batch / "jobs.json")})
    core.save_json(batch / "environment.json", {"python": sys.version, "platform": platform.platform(),
                    "experiment_commit": commit, "worktree_dirty": dirty, "created_at": core.utc(),
                    "fixture_kind": "synthetic", "filesystem_isolation": "not_enforced", "network_isolation": "not_enforced"})


def verify_batch(batch):
    manifest = json.loads((batch / "manifest.json").read_text())
    if manifest["scripts"] != current_scripts():
        raise RuntimeError("Runner/checker dependencies changed; start a new daily batch")
    for case_id, expected in manifest["cases"].items():
        if core.digest(batch / "inputs" / f"{case_id}.json") != expected:
            raise RuntimeError(f"Frozen case changed: {case_id}; refusing to grade")
    for relative, key in (("tools/daily_checks.py", "checker_sha256"), ("config.json", "config_sha256"), ("jobs.json", "jobs_sha256")):
        if core.digest(batch / relative) != manifest[key]:
            raise RuntimeError(f"Frozen {relative} changed; refusing to grade")


@contextmanager
def fixture_server(pages, requests):
    """Serve only an in-memory route map, never the repository or reviewer files."""
    if not pages:
        yield "http://fixture.invalid"
        return

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = unquote(urlsplit(self.path).path)
            status = 200 if path in pages else 404
            requests.append({"path": path, "status": status})
            content = pages.get(path, "Page unavailable").encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def capture_phase(data, phase_index, workspace, snapshots):
    for check in data["checks"]:
        if check.get("phase") == phase_index:
            original = safe_file(workspace, check["path"])
            if original.is_file() and original.stat().st_size <= 2_000_000:
                target = safe_file(snapshots / f"phase-{phase_index:02d}", check["path"])
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(original, target)


SUM_FIELDS = [field for field in METRIC_FIELDS if field not in {
    "session_id", "session_ids", "end_reason", "metrics_source", "metrics_scope", "metrics_warnings", "usage_source"}]


def aggregate_metrics(phases):
    result = {}
    for field in SUM_FIELDS:
        values = [p.get("metrics", {}).get(field) for p in phases]
        result[field] = sum(values) if values and all(type(v) in (int, float) for v in values) else None
    result["metrics_scope"] = "sum_of_fresh_phase_sessions_including_compression_children"
    result["metrics_warnings"] = [f"phase {i}: {w}" for i, p in enumerate(phases, 1)
                                  for w in p.get("metrics", {}).get("metrics_warnings", [p.get("metrics_error", "Metrics unavailable")])]
    result["session_ids"] = [sid for p in phases for sid in p.get("metrics", {}).get("session_ids", [])]
    return result


def write_daily_reports(batch):
    write_reports(batch)  # Reuse lossless JSONL/CSV collection, including archived attempts.
    rows = [json.loads(line) for line in (batch / "results.jsonl").read_text().splitlines()]
    planned = len(json.loads((batch / "jobs.json").read_text()))
    lines = ["# Daily-task evaluation results", "", f"Planned jobs: **{planned}**. Recorded attempts including archived interruptions: **{len(rows)}**.", "",
             "These are synthetic, fixed-input tasks. PASS means the documented objective artifact checks passed; prose quality, live integrations and real-world time saved are not scored.", "",
             "Process stops and artifact outcomes are separate. Missing usage remains unknown. Per-phase main/session usage is aggregated, with auxiliary usage recorded separately.", "",
             "| Case | Variant | Budget | Effort | PASS | FAIL | Other | PASS / all recorded attempts | Mean agent seconds |",
             "| --- | --- | --- | --- | ---: | ---: | ---: | --- | --- |"]
    groups = {}
    for row in rows:
        key = tuple(str(row.get(field, "unknown")) for field in ("case_id", "variant", "budget_name", "reasoning_effort"))
        groups.setdefault(key, []).append(row)
    for key, group in sorted(groups.items()):
        passed = sum(r.get("verdict") == "PASS" for r in group)
        failed = sum(r.get("verdict") == "FAIL" for r in group)
        times = [r["elapsed_seconds"] for r in group if type(r.get("elapsed_seconds")) in (int, float)]
        elapsed = f"{sum(times)/len(times):.2f} ({len(times)}/{len(group)} recorded)" if times else "unknown"
        lines.append("| " + " | ".join([*key, str(passed), str(failed), str(len(group)-passed-failed), f"{passed}/{len(group)}", elapsed]) + " |")
    lines += ["", "Each attempt retains `check.json` with individual failed checks, phase prompts/transcripts/session exports, and final files. `results.csv` retains additional metrics and errors.", "",
              "The local backend does not enforce filesystem or network isolation. Reviewer files are outside the task workspace, but accessibility is not an enforced blind boundary. Requested reasoning strength is not independently verified."]
    (batch / "summary.md").write_text("\n".join(lines) + "\n")


def run_attempt(config, batch, job):
    run = batch / "runs" / job["run_id"]
    run.mkdir(parents=True)
    workspace = run / "workspace"
    workspace.mkdir()
    record = {**job, "started_at": core.utc(), "verdict": "SETUP_ERROR", "process_status": "setup_error",
              "provider": "glimmer", "model": config["model"], "source": str(workspace), "fixture_kind": "synthetic",
              "filesystem_isolation": "not_enforced", "network_isolation": "not_enforced", "reasoning_verified": False,
              "reasoning_control": "custom_provider.extra_body.chat_template_kwargs.reasoning_strength", "phases": []}
    core.save_json(run / "running.json", record)
    started = time.monotonic()
    interrupted = False
    requests = []
    try:
        verify_batch(batch)
        case = read_case(job["case_id"], batch / "inputs")
        record.update(title=case["title"], scope=case["scope"], provenance=case["provenance"])
        raw_data = case["variants"][job["variant"]]
        with fixture_server(raw_data["web_files"], requests) as base_url:
            record["fixture_base_url"] = base_url
            data = expand(raw_data, base_url)
            staged = {name for p in data["phases"] for name in p.get("provide_before", [])}
            for name, content in data["files"].items():
                if name in staged:
                    continue
                target = safe_file(workspace, name)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            (workspace / "outputs").mkdir(exist_ok=True)
            record["setup_seconds"] = round(time.monotonic() - started, 3)
            deadline = time.monotonic() + job["max_seconds"]
            phase_count = len(data["phases"])
            for number, p in enumerate(data["phases"], 1):
                task_remaining = deadline - time.monotonic()
                if task_remaining <= 0:
                    record["process_status"] = "timed_out"
                    break
                remaining = task_remaining / (phase_count - number + 1)
                for name in p["remove_before"]:
                    safe_file(workspace, name).unlink(missing_ok=True)
                for name in p.get("provide_before", []):
                    target = safe_file(workspace, name)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(data["files"][name], encoding="utf-8")
                phase_dir = run / "phases" / f"phase-{number:02d}"
                home = phase_dir / "hermes-home"
                home.mkdir(parents=True)
                turns = job["max_turns"] // phase_count + (1 if number <= job["max_turns"] % phase_count else 0)
                prompt = p["prompt"] + f"\nWork only in {workspace}. Do not read reviewer files or other folders. "
                prompt += "Use only the supplied files and, when applicable, the supplied loopback HTTP pages. Do not use external websites. "
                prompt += f"This phase has {turns} tool-calling iterations and a {remaining:.1f}-second phase allowance; {task_remaining:.1f} seconds remain in the whole task.\n"
                (phase_dir / "prompt.md").write_text(prompt)
                core.save_json(home / "config.yaml", core.hermes_config(config, workspace, job["reasoning_effort"]))
                env = core.agent_env(config, home, workspace)
                command = config["hermes_command"] + ["--profile", "default", "chat", "--cli", "--oneshot", "--ignore-rules", "--toolsets", "terminal,file",
                           "--provider", "glimmer-eval", "--model", config["model"], "--reasoning", job["reasoning_effort"],
                           "--query-file", str(phase_dir / "prompt.md"), "--max-turns", str(turns), "--run-budget", str(remaining), "--verbose"]
                core.save_json(phase_dir / "command.json", command)
                process = core.logged(command, workspace, phase_dir / "transcript.log", remaining, env)
                item = {"phase": number, "home": str(home), "max_turns": turns, "max_seconds": remaining, **process}
                record["phases"].append(item)
                record["process_status"] = process["status"] if process["exit_code"] == 0 or process["status"] != "completed" else "hermes_nonzero_exit"
                interrupted = process["status"] == "interrupted"
                capture_phase(data, number, workspace, run / "snapshots")
                try:
                    export = core.logged(config["hermes_command"] + ["--profile", "default", "sessions", "export", str(phase_dir / "session.jsonl"),
                                         "--format", "jsonl", "--redact"], workspace, phase_dir / "export.log", 30, env)
                    if export["status"] == "interrupted":
                        raise KeyboardInterrupt
                    if export["exit_code"] != 0 or export["status"] != "completed":
                        raise ValueError("Session export failed; inspect phase export.log")
                    item["metrics"] = extract_attempt_metrics(phase_dir / "session.jsonl", workspace, home / "state.db")
                    item.update(core.auxiliary_metrics(home, None))
                    if process["status"] in {"timed_out", "interrupted"}:
                        item["metrics"]["metrics_warnings"].append("Termination may omit pending provider responses/usage")
                except (OSError, ValueError) as exc:
                    item["metrics_error"] = str(exc)
                core.save_json(phase_dir / "result.json", item)
                if interrupted or process["status"] == "timed_out":
                    break
            record["elapsed_seconds"] = round(sum(p["elapsed_seconds"] for p in record["phases"]), 3)
            if any(p["status"] == "interrupted" for p in record["phases"]):
                record["process_status"] = "interrupted"
            elif any(p["status"] == "timed_out" for p in record["phases"]):
                record["process_status"] = "timed_out"
            elif any(p["exit_code"] != 0 for p in record["phases"]):
                record["process_status"] = "hermes_nonzero_exit"
            record["metrics"] = aggregate_metrics(record["phases"])
            for field in ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens", "reasoning_tokens", "total_tokens", "api_calls"):
                values = [p.get("auxiliary_" + field) for p in record["phases"]]
                record["auxiliary_" + field] = sum(values) if values and all(type(v) in (int, float) for v in values) else None
            record["all_recorded_total_tokens"] = (record["metrics"]["total_tokens"] + record["auxiliary_total_tokens"]
                if record["metrics"]["total_tokens"] is not None and record["auxiliary_total_tokens"] is not None else None)
            record["completed_phases"] = len(record["phases"])
            record["expected_phases"] = phase_count
            verify_batch(batch)
            core.save_json(run / "web-requests.json", requests)
            command = [sys.executable, "-B", "-I", str(batch / "tools/daily_checks.py"), "--case", str(batch / "inputs" / f"{job['case_id']}.json"),
                       "--variant", job["variant"], "--workspace", str(workspace), "--base-url", base_url,
                       "--snapshots", str(run / "snapshots"), "--requests", str(run / "web-requests.json"), "--result", str(run / "check.json")]
            checked = core.logged(command, ROOT, run / "check.log", config["check_timeout_seconds"])
            if checked["status"] == "interrupted":
                raise KeyboardInterrupt
            record["check_exit_code"] = checked["exit_code"]
            record["verdict"] = {0: "PASS", 1: "FAIL", 2: "CHECK_ERROR"}.get(checked["exit_code"], "CHECK_ERROR") if checked["status"] == "completed" else "CHECK_ERROR"
            if len(record["phases"]) != phase_count and record["verdict"] == "PASS":
                record.update(verdict="FAIL", error="Not all requested phases were attempted")
            if (run / "check.json").is_file():
                check = json.loads((run / "check.json").read_text())
                record.update(passed_checks=check["passed_checks"], total_checks=check["total_checks"])
            verify_batch(batch)
    except KeyboardInterrupt:
        interrupted = True
        record.update(verdict="UNKNOWN", process_status="interrupted", error="Interrupted during execution or evidence collection")
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        record["error"] = str(exc)
        if record["process_status"] != "setup_error":
            record.update(verdict="EVIDENCE_ERROR", process_status="evidence_error")
    finally:
        record["total_seconds"] = round(time.monotonic() - started, 3)
        record["ended_at"] = core.utc()
        core.save_json(run / "web-requests.json", requests)
        core.save_json(run / "result.json", record)
        (run / "running.json").unlink(missing_ok=True)
        write_daily_reports(batch)
    print(f"{job['run_id']}: {record['verdict']} ({record['process_status']})", flush=True)
    return interrupted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config/evaluation-daily.json")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--cases", nargs="+", choices=CASE_IDS)
    selection.add_argument("--all", action="store_true", help="Select all 15 cases")
    parser.add_argument("--variants", nargs="+", choices=VARIANTS)
    parser.add_argument("--efforts", nargs="+", choices=sorted(core.EFFORTS))
    parser.add_argument("--budgets", nargs="+")
    parser.add_argument("--repeats", type=int)
    parser.add_argument("--dry-run", action="store_true", help="Print jobs; no writes, model requests or downloads")
    parser.add_argument("--prepare-only", action="store_true", help="Freeze fixtures/config; no server, credentials or Hermes needed")
    parser.add_argument("--resume", type=Path)
    args = parser.parse_args()
    if args.resume and any((args.cases, args.all, args.variants, args.efforts, args.budgets, args.repeats is not None)):
        parser.error("Resume uses the existing frozen matrix; filters cannot change it")
    config = json.loads((args.resume / "config.json" if args.resume else args.config).read_text())
    for option, key in ((args.cases, "cases"), (args.variants, "variants"), (args.efforts, "reasoning_efforts")):
        if option:
            config[key] = option
    if args.all:
        config["cases"] = CASE_IDS
    if args.repeats is not None:
        config["repeats"] = args.repeats
    if args.budgets:
        if set(args.budgets) - {b["name"] for b in config["budgets"]}:
            parser.error("Unknown budget name")
        config["budgets"] = [b for b in config["budgets"] if b["name"] in args.budgets]
    validate_config(config, args.resume / "inputs" if args.resume else None)
    jobs = make_jobs(config)
    print(f"{len(jobs)} sequential daily-task runs; maximum agent time {sum(j['max_seconds'] for j in jobs)/3600:.2f} hours, plus setup/export/checks.")
    if args.dry_run:
        for job in jobs:
            print(f"{job['run_id']}: {job['max_turns']} iterations across all phases / {job['max_seconds']} seconds")
        return 0
    if sys.version_info < (3, 12) or os.name != "posix":
        parser.error("Use Python 3.12+ on Linux or macOS")
    batch = args.resume.resolve() if args.resume else ROOT / ".runs/daily-evaluation" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    batch.mkdir(parents=True, exist_ok=bool(args.resume))
    print(f"Batch: {batch}", flush=True)
    lock = batch / ".runner-lock"
    core.acquire_lock(lock)
    try:
        if args.resume:
            verify_batch(batch)
            if json.loads((batch / "jobs.json").read_text()) != jobs:
                raise RuntimeError("Frozen jobs no longer match configuration")
        else:
            freeze_batch(config, batch)
        if args.prepare_only:
            write_daily_reports(batch)
            return 0
        core.preflight(config, batch)
        for i, job in enumerate(jobs, 1):
            run = batch / "runs" / job["run_id"]
            if (run / "result.json").exists():
                print(f"[{i}/{len(jobs)}] preserved {job['run_id']}", flush=True)
                continue
            if run.exists():
                archive = batch / "incomplete" / (job["run_id"] + "-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ"))
                archive.parent.mkdir(exist_ok=True)
                run.rename(archive)
                core.save_json(archive / "result.json", {**job, "verdict": "UNKNOWN", "process_status": "supervisor_interrupted", "error": "Unfinished attempt archived before a fresh retry"})
            print(f"[{i}/{len(jobs)}] starting {job['run_id']}", flush=True)
            if run_attempt(config, batch, job):
                return 130
        write_daily_reports(batch)
        print(f"Reports: {batch / 'results.csv'} and {batch / 'summary.md'}", flush=True)
        return 0
    finally:
        shutil.rmtree(lock)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("Interrupted; completed results preserved. Resume with the printed batch path.", file=sys.stderr)
        sys.exit(130)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, KeyError) as exc:
        print(f"Daily evaluation stopped: {exc}", file=sys.stderr)
        sys.exit(2)
