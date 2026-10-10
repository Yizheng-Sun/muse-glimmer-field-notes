#!/usr/bin/env python3
"""Run a sequential Hermes budget/reasoning matrix. Standard library only."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import difflib
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import platform
import random
import re
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import time
from urllib.parse import urlparse
from urllib.request import build_opener, ProxyHandler, Request

from eval_metrics import extract_attempt_metrics, write_reports

ROOT = Path(__file__).resolve().parents[1]
EFFORTS = {"low", "medium", "high", "xhigh"}
TARGETS = {
    "C01": ["tests/test_options.py", "-k", "envvar"],
    "C02": ["tests/test_utils/test_make_default_short_help.py"],
    "C03": ["tests/test_requirements.py"],
    "C04": ["tests/test_metadata.py", "-k", "license_files"],
}
EXCLUDE = {".git", ".venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def load_config(path):
    config = json.loads(path.read_text())
    if not config.get("cases") or any(c not in TARGETS for c in config["cases"]):
        raise ValueError("cases must select C01–C04")
    if not config.get("reasoning_efforts") or any(e not in EFFORTS for e in config["reasoning_efforts"]):
        raise ValueError("reasoning_efforts must select low, medium, high, xhigh")
    budgets = config.get("budgets", [])
    names = [b["name"] for b in budgets]
    if not budgets or len(set(names)) != len(names):
        raise ValueError("Provide budgets with unique names")
    for b in budgets:
        if not re.fullmatch(r"[a-z][a-z0-9_-]{0,30}", b["name"]):
            raise ValueError("Budget names must be simple lowercase labels")
        if type(b["max_turns"]) is not int or b["max_turns"] < 1:
            raise ValueError("max_turns must be a positive integer")
        if type(b["max_seconds"]) not in (int, float) or not 0 < b["max_seconds"] <= 86400:
            raise ValueError("max_seconds must be positive and at most one day")
    if type(config.get("repeats")) is not int or config["repeats"] < 1:
        raise ValueError("repeats must be a positive integer")
    if len(set(config["cases"])) != len(config["cases"]) or len(set(config["reasoning_efforts"])) != len(config["reasoning_efforts"]):
        raise ValueError("Duplicate cases/efforts would silently repeat jobs")
    endpoint = urlparse(config["base_url"])
    if endpoint.scheme != "http" or endpoint.hostname not in {"localhost", "127.0.0.1", "::1"} or endpoint.username or endpoint.password:
        raise ValueError("Use the local model's loopback HTTP /v1 URL; credentials belong in the API-key environment variable")
    if endpoint.path.rstrip("/") != "/v1" or endpoint.query or endpoint.fragment:
        raise ValueError("base_url must end in /v1")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", config["api_key_env"]):
        raise ValueError("Invalid api_key_env name")
    if not isinstance(config["hermes_command"], list) or not config["hermes_command"] or any(not isinstance(x, str) for x in config["hermes_command"]):
        raise ValueError("hermes_command must be an argv list, e.g. [\"hermes\"]")
    for key in ("pytest_version", "flit_core_version"):
        if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)+", config[key]):
            raise ValueError(f"Pin {key} to a numeric release")
    if not 0 < config.get("check_timeout_seconds", 120) <= 600:
        raise ValueError("check_timeout_seconds must be positive and <=600")
    if type(config.get("context_length")) is not int or not 1024 <= config["context_length"] <= 131072:
        raise ValueError("context_length must match the server slot, between 1024 and 131072")
    sampling = config.get("sampling", {})
    if set(sampling) != {"temperature", "top_p", "top_k"} or any(type(sampling[k]) not in (int, float) or not math.isfinite(sampling[k]) for k in ("temperature", "top_p")) or not 0 <= sampling["temperature"] <= 2 or not 0 < sampling["top_p"] <= 1 or type(sampling["top_k"]) is not int or sampling["top_k"] < 1:
        raise ValueError("Provide sampling temperature (0–2), top_p (0–1), and positive integer top_k")
    return config


def make_jobs(config):
    jobs = []
    for case, budget, effort, repeat in itertools.product(config["cases"], config["budgets"], config["reasoning_efforts"], range(1, config["repeats"] + 1)):
        jobs.append({"run_id": f"{case}-{budget['name']}-{effort}-r{repeat:02d}",
                     "case_id": case, "budget_name": budget["name"], "reasoning_effort": effort,
                     "repeat": repeat, "max_turns": budget["max_turns"], "max_seconds": budget["max_seconds"]})
    random.Random(config.get("shuffle_seed", 42)).shuffle(jobs)
    return jobs


def logged(argv, cwd, log, timeout, env=None):
    """Save output as it arrives, stop the process group on timeout/interrupt."""
    started = time.monotonic()
    status = "completed"
    with log.open("w") as output:
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            proc.wait(timeout=timeout)
        except (subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
            status = "interrupted" if isinstance(exc, KeyboardInterrupt) else "timed_out"
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait()
    return {"exit_code": proc.returncode, "status": status,
            "elapsed_seconds": round(time.monotonic() - started, 3)}


def require_logged(argv, cwd, log, timeout=300, env=None):
    result = logged(argv, cwd, log, timeout, env)
    if result["status"] == "interrupted":
        raise KeyboardInterrupt
    if result["exit_code"] != 0 or result["status"] != "completed":
        raise RuntimeError(f"Setup command failed ({result['status']}, exit {result['exit_code']}); inspect {log}")
    return result


def hermes_config(config, source, effort):
    """JSON is valid YAML; no PyYAML dependency in this wrapper."""
    provider = "glimmer-eval"
    url = config["base_url"].rstrip("/")
    extra = {"chat_template_kwargs": {"reasoning_strength": effort},
             "parallel_tool_calls": False, **config["sampling"]}
    auxiliary = {"provider": provider, "model": config["model"], "timeout": 300, "extra_body": extra}
    return {
        "model": {"default": config["model"], "provider": provider, "base_url": url, "context_length": config["context_length"]},
        "providers": {provider: {"api": url, "key_env": config["api_key_env"],
                                 "default_model": config["model"], "transport": "chat_completions", "extra_body": extra}},
        "terminal": {"backend": "local", "cwd": str(source)},
        "agent": {"reasoning_effort": effort},
        "memory": {"memory_enabled": False, "user_profile_enabled": False, "provider": ""},
        "auxiliary": {"compression": auxiliary, "approval": auxiliary,
                      "title_generation": {"enabled": False, "model_upgrade_enabled": False},
                      "background_review": {"enabled": False}},
        "fallback_providers": [], "mcp_servers": {},
    }


def agent_env(config, home, source):
    env = os.environ.copy()
    # Fresh home/config/DB, never copy the user's credentials or memory files.
    for key in list(env):
        if key.startswith(("HERMES_", "TERMINAL_")) or key in {"OPENAI_BASE_URL", "OPENAI_API_BASE", "OPENAI_API_KEY", "PYTHONPATH"}:
            env.pop(key)
    env.update({"HERMES_HOME": str(home), "TERMINAL_CWD": str(source),
                "TERMINAL_BACKEND": "local", "HERMES_IGNORE_RULES": "1",
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
                "PYTHONUNBUFFERED": "1", "PATH": str(source / ".venv/bin") + os.pathsep + env.get("PATH", ""),
                "GIT_CEILING_DIRECTORIES": str(source.parent),
                "NO_PROXY": "localhost,127.0.0.1,::1", "no_proxy": "localhost,127.0.0.1,::1"})
    # A no-auth local server still needs a nonempty SDK key; never record its value.
    env[config["api_key_env"]] = os.environ.get(config["api_key_env"], "local-no-auth")
    return env


def preflight(config, batch):
    result = require_logged(config["hermes_command"] + ["chat", "--help"], ROOT, batch / "hermes-help.log", 30)
    help_text = (batch / "hermes-help.log").read_text()
    for flag in ("--cli", "--oneshot", "--query-file", "--max-turns", "--run-budget", "--reasoning", "--ignore-rules", "--toolsets"):
        if flag not in help_text:
            raise RuntimeError(f"Installed Hermes lacks {flag}; use the working Hermes version that supports evaluation flags")
    require_logged(config["hermes_command"] + ["--version"], ROOT, batch / "hermes-version.log", 30)
    req = Request(config["base_url"].rstrip("/") + "/models")
    if os.environ.get(config["api_key_env"]):
        req.add_header("Authorization", "Bearer " + os.environ[config["api_key_env"]])
    with build_opener(ProxyHandler({})).open(req, timeout=10) as response:
        models = json.load(response)
    if config["model"] not in [m.get("id") for m in models.get("data", [])]:
        raise RuntimeError(f"Configured model alias {config['model']!r} is absent from the local server's /v1/models")
    save_json(batch / "server-models.json", models)
    return result


def prepare_batch(config, batch):
    """Download/verify sources and wheels outside any scored timer."""
    for case in config["cases"]:
        require_logged([sys.executable, str(ROOT / "scripts/prepare_case.py"), case, "--verify"],
                       ROOT, batch / f"prepare-{case}.log", 900)
        frozen = batch / "inputs" / case
        if frozen.exists():
            shutil.rmtree(frozen)
        frozen.mkdir(parents=True)
        shutil.copytree(ROOT / ".runs/coding" / case / "base", frozen / "base",
                        ignore=shutil.ignore_patterns(*EXCLUDE, "*.pyc"))
        for name in ("case.json", "prompt.md", "check.py"):
            shutil.copyfile(ROOT / "cases/coding" / case / name, frozen / name)
        save_json(frozen / "manifest.json", {"base": files(frozen / "base"),
                  "check_sha256": digest(frozen / "check.py"), "prompt_sha256": digest(frozen / "prompt.md"),
                  "case_sha256": digest(frozen / "case.json")})
    wheels = batch / "wheels"
    wheels.mkdir(exist_ok=True)
    require_logged([sys.executable, "-m", "pip", "download", "--only-binary=:all:", "--dest", str(wheels),
                    f"pytest=={config['pytest_version']}", f"flit_core=={config['flit_core_version']}"],
                   ROOT, batch / "download-wheels.log", 600)
    save_json(batch / "wheel-hashes.json", {p.name: digest(p) for p in sorted(wheels.glob("*.whl"))})


def verify_inputs(batch, case):
    frozen = batch / "inputs" / case
    manifest = json.loads((frozen / "manifest.json").read_text())
    for name, key in (("check.py", "check_sha256"), ("prompt.md", "prompt_sha256"), ("case.json", "case_sha256")):
        if digest(frozen / name) != manifest[key]:
            raise RuntimeError(f"Frozen {case}/{name} changed; refusing this batch")
    if files(frozen / "base") != manifest["base"]:
        raise RuntimeError(f"Frozen {case} baseline changed; refusing this batch")
    return manifest


def files(source):
    result = {}
    for folder, dirs, names in os.walk(source, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDE and not (Path(folder) / d).is_symlink())
        for name in sorted(names):
            if name.endswith((".pyc", ".pyo")):
                continue
            path = Path(folder) / name
            rel = path.relative_to(source).as_posix()
            result[rel] = ("symlink:" + os.readlink(path)) if path.is_symlink() else digest(path)
    return result


def save_patch(base, source, run):
    before, after = files(base), files(source)
    changed = [p for p in sorted(before.keys() | after.keys()) if before.get(p) != after.get(p)]
    save_json(run / "source-changes.json", {"before": before, "after": after, "changed_files": changed})
    with (run / "source.patch").open("w") as output:
        for name in changed:
            try:
                old, new = base / name, source / name
                if old.is_symlink() or new.is_symlink():
                    raise ValueError("symlink")
                left = old.read_text().splitlines(keepends=True) if old.exists() else []
                right = new.read_text().splitlines(keepends=True) if new.exists() else []
                output.writelines(difflib.unified_diff(left, right, "a/" + name, "b/" + name))
            except (UnicodeError, OSError, ValueError):
                output.write(f"Binary or symlink change: {name}\n")
    return changed


def setup_attempt(config, batch, run, source):
    case = run.name.split("-", 1)[0]
    shutil.copytree(batch / "inputs" / case / "base", source,
                    ignore=shutil.ignore_patterns(*EXCLUDE, "*.pyc"))
    # A single synthetic base commit makes agent Git commands describe its own
    # source, without upstream history, fixed revision, or ancestor repo metadata.
    log = run / "source-git.log"
    require_logged(["git", "init", "--quiet", str(source)], ROOT, log)
    require_logged(["git", "add", "-A"], source, run / "source-git-add.log")
    require_logged(["git", "-c", "core.hooksPath=/dev/null", "-c", "user.name=Evaluation", "-c", "user.email=evaluation@localhost",
                    "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "Starting source"],
                   source, run / "source-git-commit.log")
    with (source / ".git/info/exclude").open("a") as ignore:
        ignore.write("\n.venv/\n__pycache__/\n.pytest_cache/\n*.pyc\n")
    require_logged([sys.executable, "-m", "venv", str(source / ".venv")], ROOT, run / "venv.log")
    python = str(source / ".venv/bin/python")
    require_logged([python, "-m", "pip", "install", "--no-index", "--find-links", str(batch / "wheels"),
                    f"pytest=={config['pytest_version']}", f"flit_core=={config['flit_core_version']}"],
                   source, run / "install.log")
    require_logged([python, "-m", "pip", "install", "--no-index", "--no-build-isolation", "--no-deps", "-e", str(source)],
                   source, run / "editable-install.log")
    require_logged([python, "-m", "pip", "freeze", "--all"], source, run / "dependencies.txt")
    test_env = os.environ.copy()
    test_env.update(PYTHONPATH=str(source / "src"), PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    require_logged([python, "-m", "pytest", "--collect-only", "-q", *TARGETS[case]],
                   source, run / "test-collection.log", 120, test_env)


def auxiliary_metrics(home, session_id):
    """Only auxiliary task rows: empty task denotes main-agent accounting."""
    db = home / "state.db"
    if not db.exists():
        return {"auxiliary_usage": None, "auxiliary_metrics_error": "state.db unavailable"}
    try:
        with sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT task, CASE WHEN COUNT(input_tokens)=COUNT(*) THEN SUM(input_tokens) END AS input_tokens, "
                "CASE WHEN COUNT(output_tokens)=COUNT(*) THEN SUM(output_tokens) END AS output_tokens, "
                "CASE WHEN COUNT(cache_read_tokens)=COUNT(*) THEN SUM(cache_read_tokens) END AS cache_read_tokens, "
                "CASE WHEN COUNT(cache_write_tokens)=COUNT(*) THEN SUM(cache_write_tokens) END AS cache_write_tokens, "
                "CASE WHEN COUNT(reasoning_tokens)=COUNT(*) THEN SUM(reasoning_tokens) END AS reasoning_tokens, "
                "CASE WHEN COUNT(api_call_count)=COUNT(*) THEN SUM(api_call_count) END AS api_calls "
                "FROM session_model_usage WHERE task <> '' GROUP BY task").fetchall()
        usage = [dict(row) for row in rows]
        result = {"auxiliary_usage": usage}
        for key in ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens", "reasoning_tokens", "api_calls"):
            values = [row[key] for row in usage]
            result["auxiliary_" + key] = sum(values) if all(v is not None for v in values) else None
        counters = [result["auxiliary_" + k] for k in ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens")]
        result["auxiliary_total_tokens"] = sum(counters) if all(v is not None for v in counters) else None
        return result
    except sqlite3.Error as error:
        return {"auxiliary_usage": None, "auxiliary_metrics_error": str(error)}


def run_attempt(config, batch, job):
    run = batch / "runs" / job["run_id"]
    run.mkdir(parents=True)
    source = run / "source"
    home = run / "hermes-home"
    home.mkdir()
    case_dir = batch / "inputs" / job["case_id"]
    record = {**job, "started_at": utc(), "verdict": "SETUP_ERROR", "process_status": "setup_error",
              "filesystem_isolation": "not_enforced", "network_isolation": "not_enforced",
              "reasoning_control": "custom_provider.extra_body.chat_template_kwargs.reasoning_strength",
              "reasoning_verified": False, "reasoning_verification": "configured; no independent request-wire capture",
              "source": str(source), "hermes_exit_code": None, "check_exit_code": None}
    save_json(run / "running.json", record)
    setup_started = time.monotonic()
    interrupted = False
    try:
        manifest = verify_inputs(batch, job["case_id"])
        setup_attempt(config, batch, run, source)
        record["setup_seconds"] = round(time.monotonic() - setup_started, 3)
        grader = run / "acceptance-check.py"
        shutil.copyfile(case_dir / "check.py", grader)
        record["check_sha256"] = digest(grader)
        record["prompt_sha256"] = digest(case_dir / "prompt.md")
        record["base_commit"] = json.loads((case_dir / "case.json").read_text())["base_commit"]
        (run / "prompt.md").write_text((case_dir / "prompt.md").read_text() +
            f"\n\nEvaluation harness instructions:\nWork only in {source}. Do not read other folders, reviewer files, or use the network. "
            "Use .venv/bin/python for Python and pytest. "
            f"Run relevant upstream tests with PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest {' '.join(TARGETS[job['case_id']])}. "
            f"You have at most {job['max_turns']} tool-calling iterations and {job['max_seconds']} seconds. "
            "Apply a minimal fix, validate it, and finish.\n")
        save_json(home / "config.yaml", hermes_config(config, source, job["reasoning_effort"]))
        env = agent_env(config, home, source)
        command = config["hermes_command"] + ["--profile", "default", "chat", "--cli", "--oneshot", "--ignore-rules", "--toolsets", "terminal,file",
                    "--provider", "glimmer-eval", "--model", config["model"], "--reasoning", job["reasoning_effort"],
                    "--query-file", str(run / "prompt.md"), "--max-turns", str(job["max_turns"]),
                    "--run-budget", str(job["max_seconds"]), "--verbose"]
        save_json(run / "command.json", command)
        process = logged(command, source, run / "transcript.log", job["max_seconds"], env)
        record.update(hermes_exit_code=process["exit_code"], elapsed_seconds=process["elapsed_seconds"], process_status=process["status"])
        interrupted = process["status"] == "interrupted"
        if process["status"] == "completed" and process["exit_code"] != 0:
            record["process_status"] = "hermes_nonzero_exit"
        transcript = (run / "transcript.log").read_text(errors="replace")
        record["iteration_budget_notice"] = "Iteration budget reached" in transcript
        try:
            ids = re.findall(r"^Session:\s+([A-Za-z0-9_-]+)\s*$", transcript, re.MULTILINE)
            session_id = ids[-1] if ids else None
            # Export the entire fresh home, including compression children. Per-
            # model database deltas and occurrence UIDs prevent double counting.
            exported = logged(config["hermes_command"] + ["--profile", "default", "sessions", "export", str(run / "session.jsonl"),
                              "--format", "jsonl", "--redact"],
                              source, run / "export.log", 30, env)
            if exported["status"] == "interrupted":
                raise KeyboardInterrupt
            if exported["exit_code"] != 0:
                raise ValueError("Hermes session export failed; inspect export.log")
            record["metrics"] = extract_attempt_metrics(run / "session.jsonl", source, home / "state.db", session_id)
            record["session_id"] = record["metrics"]["session_id"]
            if process["status"] in {"timed_out", "interrupted"}:
                record["metrics"]["metrics_warnings"].append("Agent was terminated; pending provider responses or queued usage may be missing")
                record["metrics_status"] = "partial_after_termination"
            else:
                record["metrics_status"] = "recorded_with_native_availability_limits"
            record.update(auxiliary_metrics(home, session_id))
            main_tokens = record["metrics"].get("total_tokens")
            aux_tokens = record.get("auxiliary_total_tokens")
            record["all_recorded_total_tokens"] = main_tokens + aux_tokens if main_tokens is not None and aux_tokens is not None else None
        except (OSError, ValueError, sqlite3.Error) as error:
            record["metrics_error"] = str(error)
        if verify_inputs(batch, job["case_id"]) != manifest:
            raise RuntimeError("Frozen input manifest changed during the run")
        if digest(grader) != manifest["check_sha256"] or digest(case_dir / "check.py") != manifest["check_sha256"]:
            raise RuntimeError("Acceptance checker changed during the run; refusing to grade")
        checked = logged([sys.executable, "-B", "-I", str(grader), "--source", str(source)], ROOT,
                         run / "check.log", config.get("check_timeout_seconds", 120))
        record["check_exit_code"] = checked["exit_code"]
        record["check_seconds"] = checked["elapsed_seconds"]
        if checked["status"] == "interrupted":
            raise KeyboardInterrupt
        record["verdict"] = {0: "PASS", 1: "FAIL", 2: "SETUP_ERROR"}.get(checked["exit_code"], "CHECK_ERROR") if checked["status"] == "completed" else "CHECK_ERROR"
        if config.get("upstream_checks", True) and not interrupted:
            upstream = logged([str(source / ".venv/bin/python"), "-m", "pytest", *TARGETS[job["case_id"]]],
                              source, run / "upstream-check.log", config.get("check_timeout_seconds", 120), env)
            record["upstream_check"] = upstream
            if upstream["status"] == "interrupted":
                raise KeyboardInterrupt
        record["changed_files"] = save_patch(case_dir / "base", source, run)
    except KeyboardInterrupt:
        interrupted = True
        record.update(process_status="interrupted", error="Interrupted during setup or evidence collection")
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        record["error"] = str(error)
        if record["process_status"] != "setup_error":
            record["process_status"] = "evidence_error"
    finally:
        record.setdefault("setup_seconds", round(time.monotonic() - setup_started, 3))
        record["total_seconds"] = round(time.monotonic() - setup_started, 3)
        record["ended_at"] = utc()
        save_json(run / "result.json", record)
        (run / "running.json").unlink(missing_ok=True)
        write_reports(batch)
    print(f"{job['run_id']}: {record['verdict']} ({record['process_status']}); {run}", flush=True)
    return interrupted


def acquire_lock(lock):
    try:
        lock.mkdir()
    except FileExistsError:
        owner = json.loads((lock / "owner.json").read_text())
        if owner["hostname"] != socket.gethostname():
            raise RuntimeError("Batch lock belongs to another host; verify that runner is stopped before removing .runner-lock")
        try:
            os.kill(owner["pid"], 0)
        except ProcessLookupError:
            shutil.rmtree(lock)
            lock.mkdir()
        else:
            raise RuntimeError(f"Batch is locked by live PID {owner['pid']}; do not run two supervisors against it")
    save_json(lock / "owner.json", {"pid": os.getpid(), "hostname": socket.gethostname(), "created_at": utc()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config/evaluation.json")
    parser.add_argument("--cases", nargs="+", choices=sorted(TARGETS))
    parser.add_argument("--efforts", nargs="+", choices=sorted(EFFORTS))
    parser.add_argument("--budgets", nargs="+", help="Named budgets from the configuration")
    parser.add_argument("--repeats", type=int)
    parser.add_argument("--dry-run", action="store_true", help="Print matrix and maximum agent time; no calls, files, or downloads")
    parser.add_argument("--prepare-only", action="store_true", help="Verify cases and cache test wheels; print batch path for --resume")
    parser.add_argument("--resume", type=Path, help="Use the frozen configuration of a previous batch; preserve all completed jobs")
    args = parser.parse_args()
    if args.resume and any((args.cases, args.efforts, args.budgets, args.repeats is not None)):
        parser.error("--resume uses the existing frozen matrix; filters/repeats cannot change it")
    config = load_config(args.resume / "config.json" if args.resume else args.config)
    if args.cases:
        config["cases"] = args.cases
    if args.efforts:
        config["reasoning_efforts"] = args.efforts
    if args.repeats is not None:
        if args.repeats < 1:
            parser.error("--repeats must be >=1")
        config["repeats"] = args.repeats
    if args.budgets:
        if set(args.budgets) - {b["name"] for b in config["budgets"]}:
            parser.error("Unknown budget name")
        config["budgets"] = [b for b in config["budgets"] if b["name"] in args.budgets]
    if len(set(config["cases"])) != len(config["cases"]) or len(set(config["reasoning_efforts"])) != len(config["reasoning_efforts"]):
        parser.error("Do not repeat case or effort filters; use --repeats instead")
    jobs = make_jobs(config)
    ceiling = sum(j["max_seconds"] for j in jobs)
    print(f"{len(jobs)} sequential runs; maximum agent time {ceiling / 3600:.2f} hours, plus setup/checks/termination grace.")
    if args.dry_run:
        for job in jobs:
            print(f"{job['run_id']}: {job['max_turns']} iterations / {job['max_seconds']} seconds")
        return 0
    if sys.version_info < (3, 12):
        parser.error("Use Python 3.12+ for safe source preparation")
    if os.name != "posix":
        parser.error("This runner targets the Linux 5090 machine (also supports macOS)")
    batch = args.resume.resolve() if args.resume else ROOT / ".runs/evaluation" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    batch.mkdir(parents=True, exist_ok=bool(args.resume))
    print(f"Batch: {batch}", flush=True)
    # Atomic mkdir prevents two processes rewriting the same batch.
    lock = batch / ".runner-lock"
    acquire_lock(lock)
    try:
        if args.resume:
            frozen_jobs = json.loads((batch / "jobs.json").read_text())
            if frozen_jobs != jobs:
                raise ValueError("Frozen matrix differs from recomputed jobs")
        else:
            save_json(batch / "config.json", config)
            save_json(batch / "jobs.json", jobs)
            save_json(batch / "environment.json", {"python": sys.version, "executable": sys.executable,
                      "platform": platform.platform(), "experiment_commit": git("rev-parse", "HEAD"),
                      "worktree_dirty": bool(git("status", "--porcelain")), "runner_sha256": digest(Path(__file__)),
                      "metrics_sha256": digest(ROOT / "scripts/eval_metrics.py"), "created_at": utc()})
        preflight(config, batch)
        if not (batch / "prepared.json").exists():
            prepare_batch(config, batch)
            save_json(batch / "prepared.json", {"prepared_at": utc()})
        for case in config["cases"]:
            verify_inputs(batch, case)
        expected_wheels = json.loads((batch / "wheel-hashes.json").read_text())
        if {p.name: digest(p) for p in (batch / "wheels").glob("*.whl")} != expected_wheels:
            raise RuntimeError("Frozen dependency wheels changed; refusing this batch")
        if args.prepare_only:
            return 0
        for index, job in enumerate(jobs, 1):
            run = batch / "runs" / job["run_id"]
            if (run / "result.json").exists():
                print(f"[{index}/{len(jobs)}] preserved {job['run_id']}", flush=True)
                continue
            if run.exists():
                # A killed supervisor leaves an unfinished directory. Keep it and
                # make a clearly labelled infrastructure retry from a fresh base.
                archive = batch / "incomplete" / (job["run_id"] + "-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ"))
                archive.parent.mkdir(exist_ok=True)
                run.rename(archive)
                save_json(archive / "result.json", {**job, "verdict": "UNKNOWN", "process_status": "supervisor_interrupted", "error": "Incomplete attempt archived before fresh infrastructure retry"})
            print(f"[{index}/{len(jobs)}] starting {job['run_id']}", flush=True)
            if run_attempt(config, batch, job):
                return 130
        write_reports(batch)
        print(f"Reports: {batch / 'results.csv'} and {batch / 'summary.md'}", flush=True)
        return 0
    finally:
        shutil.rmtree(lock)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("Interrupted; completed results preserved. Resume using the printed batch path.", file=sys.stderr)
        sys.exit(130)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Evaluation stopped: {error}", file=sys.stderr)
        sys.exit(2)
