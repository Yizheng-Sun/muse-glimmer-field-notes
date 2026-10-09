#!/usr/bin/env python3
"""Prepare pinned coding sources and optionally verify or export one case.

Standard library + Git only. Does not invoke Hermes, a model, or scored runs.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / ".runs"


def command(*args):
    return subprocess.check_output(args, text=True, cwd=ROOT).strip()


def snapshot(cache, revision, destination):
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("A full, lowercase commit hash is required")
    exists = subprocess.run(
        ["git", "--git-dir", str(cache), "cat-file", "-e", revision + "^{commit}"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    ).returncode == 0
    if not exists:
        subprocess.run(["git", "--git-dir", str(cache), "fetch", "--depth=1",
                        "origin", revision], check=True)
    resolved = command("git", "--git-dir", str(cache), "rev-parse", revision + "^{commit}")
    if resolved != revision:
        raise ValueError("Fetched revision does not match the pinned commit")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
        temporary = Path(temporary)
        archive = temporary / "source.tar"
        with archive.open("wb") as handle:
            subprocess.run(["git", "--git-dir", str(cache), "archive", revision],
                           stdout=handle, check=True)
        extracted = temporary / "source"
        extracted.mkdir()
        with tarfile.open(archive) as handle:
            handle.extractall(extracted, filter="data")
        if any(path.name == ".git" for path in extracted.rglob(".git")):
            raise ValueError("Source snapshot unexpectedly contains Git history")
        # Only preparation references are regenerated, never an exported agent copy.
        if destination.exists():
            shutil.rmtree(destination)
        extracted.rename(destination)


def check(case_dir, source, logs, name):
    args = [sys.executable, "-B", "-I", str(case_dir / "check.py"), "--source", str(source)]
    started = time.monotonic()
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=120)
    output = result.stdout + result.stderr
    log = logs / (name + ".log")
    log.write_text(output)
    return {"source": str(source.relative_to(ROOT)), "exit_code": result.returncode,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "log": str(log.relative_to(ROOT)), "output": output}


def prepare(case_id, verify, export):
    started = time.monotonic()
    case_dir = ROOT / "cases" / "coding" / case_id
    case = json.loads((case_dir / "case.json").read_text())
    match = re.fullmatch(r"https://github.com/([\w.-]+)/([\w.-]+?)(?:\.git)?", case["repo_url"])
    if not match or case["id"] != case_id:
        raise ValueError("Invalid GitHub repository or case ID")
    cache = RUNS / "cache" / ("-".join(match.groups()) + ".git")
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init", "--bare", "--quiet", str(cache)], check=True)
        subprocess.run(["git", "--git-dir", str(cache), "remote", "add", "origin",
                        case["repo_url"]], check=True)
    elif command("git", "--git-dir", str(cache), "remote", "get-url", "origin") != case["repo_url"]:
        raise ValueError("Cache remote does not match case metadata")
    folder = RUNS / "coding" / case_id
    snapshot(cache, case["base_commit"], folder / "base")
    snapshot(cache, case["fixed_commit"], folder / "fixed")
    print(f"{case_id}: prepared pinned base and fixed source snapshots", flush=True)
    if verify:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        logs = folder / "logs" / stamp
        logs.mkdir(parents=True)
        report = {
            "case_id": case_id, "verified_at": stamp,
            "experiment_commit": command("git", "rev-parse", "HEAD"),
            "experiment_worktree_dirty": bool(command("git", "status", "--porcelain")),
            "base_commit": case["base_commit"], "fixed_commit": case["fixed_commit"],
            "check_sha256": hashlib.sha256((case_dir / "check.py").read_bytes()).hexdigest(),
            "prompt_sha256": hashlib.sha256((case_dir / "prompt.md").read_bytes()).hexdigest(),
            "helper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "environment": {"python": sys.version, "executable": sys.executable,
                            "platform": platform.platform(), "machine": platform.machine(),
                            "git": command("git", "--version"), "dependencies": "none"},
            "base": check(case_dir, folder / "base", logs, "base"),
            "fixed": check(case_dir, folder / "fixed", logs, "fixed"),
        }
        report["prepared_locally"] = report["base"]["exit_code"] == 1 and report["fixed"]["exit_code"] == 0
        report["preparation_elapsed_seconds"] = round(time.monotonic() - started, 3)
        (logs / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
        print(f"{case_id}: base={report['base']['exit_code']} fixed={report['fixed']['exit_code']}; "
              f"report {logs.relative_to(ROOT)}/verification.json", flush=True)
        if not report["prepared_locally"]:
            raise RuntimeError("Expected behavioral failure (1) before and pass (0) after")
    if export:
        agent = folder / "agent"
        if agent.exists():
            raise FileExistsError(f"Refusing to overwrite {agent.relative_to(ROOT)}; preserve any agent edits")
        agent.mkdir()
        shutil.copytree(folder / "base", agent / "source",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copyfile(case_dir / "prompt.md", agent / "prompt.md")
        print(f"{case_id}: exported {agent.relative_to(ROOT)} (prompt + broken source only)", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=["C01", "C02", "C03", "C04", "all"])
    parser.add_argument("--verify", action="store_true", help="require failing base and passing fixed checks")
    parser.add_argument("--export", action="store_true", help="also create a new agent copy; never overwrite it")
    args = parser.parse_args()
    if sys.version_info < (3, 12):
        parser.error("Use Python 3.12+ for safe tar extraction; upstream code itself supports 3.10+")
    for case_id in (["C01", "C02", "C03", "C04"] if args.case == "all" else [args.case]):
        prepare(case_id, args.verify, args.export)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Preparation failed: {error}", file=sys.stderr)
        sys.exit(2)
