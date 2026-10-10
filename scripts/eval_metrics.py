#!/usr/bin/env python3
"""Read Hermes session exports and rebuild lightweight coding evaluation reports.

Only recorded counters are used for token usage. Hermes canonical input excludes
cache hits/writes: ``prompt_tokens`` adds those counters, and ``total_tokens``
adds output. Reasoning is an output detail and is never added a second time.
Native session exports cover the main agent session, omitting auxiliary-task
usage. Message-derived counts include inactive/rewound messages: those calls still cost
work. Active counts are additionally exposed for inspecting the retained history.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
import io
import json
import math
import sqlite3
from pathlib import Path
from statistics import mean
from typing import Any


METRIC_FIELDS = (
    "session_id", "session_ids", "input_tokens", "output_tokens", "prompt_tokens", "total_tokens",
    "uncached_input_output_tokens",
    "reasoning_tokens", "cache_read_tokens", "cache_write_tokens", "api_calls",
    "assistant_turns", "tool_iterations", "tool_calls", "user_messages",
    "session_elapsed_seconds", "end_reason", "metrics_source", "metrics_scope", "metrics_warnings",
    "reported_tool_calls", "active_assistant_turns", "inactive_assistant_turns",
    "active_tool_calls", "inactive_tool_calls", "inactive_message_count",
    "observed_message_count", "api_calls_with_usage", "usage_source",
)
REPORT_FIELDS = (
    "run_id", "case_id", "budget_name", "reasoning_effort", "repeat",
    "max_turns", "max_seconds", "verdict", "process_status", "hermes_exit_code",
    "check_exit_code", "elapsed_seconds", "setup_seconds", "reasoning_verified",
    "error", *METRIC_FIELDS, "auxiliary_input_tokens", "auxiliary_output_tokens",
    "auxiliary_cache_read_tokens", "auxiliary_cache_write_tokens",
    "auxiliary_reasoning_tokens", "auxiliary_total_tokens", "auxiliary_usage",
)


def _sessions(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        if any(not isinstance(item, dict) for item in value):
            raise ValueError("Session export list contains a non-object entry")
        return value
    if isinstance(value, dict):
        if isinstance(value.get("sessions"), list):
            return _sessions(value["sessions"])
        return [value]
    raise ValueError("Session export must contain a JSON object or list of objects")


def _read_sessions(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    try:
        candidates = _sessions(json.loads(text))
    except json.JSONDecodeError:
        candidates = []
        for line_number, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                candidates.extend(_sessions(json.loads(line)))
            except (ValueError, json.JSONDecodeError) as exc:
                raise ValueError(f"Invalid session JSON on line {line_number}: {exc}") from exc
    if not candidates:
        raise ValueError("Session export is empty")
    return candidates


def _read_session(path: Path, session_id: str | None) -> dict[str, Any]:
    candidates = _read_sessions(path)
    if session_id is not None:
        matching = [item for item in candidates if str(item.get("id", item.get("session_id"))) == session_id]
        if not matching:
            raise ValueError(f"Session {session_id!r} was not found in export")
        return matching[-1]  # Repeated snapshots are not additive usage records.
    identifiers = {item.get("id", item.get("session_id")) for item in candidates}
    if len(identifiers) > 1:
        raise ValueError("Export contains multiple sessions; supply --session-id")
    return candidates[-1]


def _counter(session: dict[str, Any], name: str, warnings: list[str]) -> int | None:
    value = session.get(name)
    if value is None:
        warnings.append(f"{name} is unavailable in the session export")
        return None
    if isinstance(value, bool):
        warnings.append(f"{name} is invalid: expected a nonnegative integer")
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        parsed = -1
    if parsed < 0 or (isinstance(value, float) and value != parsed):
        warnings.append(f"{name} is invalid: expected a nonnegative integer")
        return None
    return parsed


def _timestamp(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(value) else None
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        # Hermes exports Unix seconds. ISO timestamps without an offset are
        # ambiguous rather than an invitation to use this machine's timezone.
        if parsed.tzinfo is None:
            return None
        return parsed.timestamp()
    return None


def _is_inactive(message: dict[str, Any]) -> bool:
    return message.get("active", True) in (False, 0, "0", "false", "False")


def _tool_calls(message: dict[str, Any], index: int, warnings: list[str]) -> list[Any] | None:
    value = message.get("tool_calls")
    if value is None:
        return []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            value = None
    if isinstance(value, list) and all(isinstance(call, dict) for call in value):
        return value
    warnings.append(f"Message {index} has malformed tool_calls; tool counts are unavailable")
    return None


def extract_session_metrics(path: Path, session_id: str | None = None) -> dict[str, Any]:
    """Extract cumulative usage and observed work from a session object/JSONL.

    Raises ``ValueError`` for malformed or ambiguous exports. Missing usage is
    ``None``. Reported API requests and observed assistant turns intentionally
    differ: providers may retry and Hermes may append a final summary message.
    """
    path = Path(path)
    session = _read_session(path, session_id)
    warnings: list[str] = []
    result: dict[str, Any] = {key: None for key in METRIC_FIELDS}
    result.update(
        session_id=session.get("id", session.get("session_id")),
        session_ids=[session.get("id", session.get("session_id"))],
        usage_source="native_session_export",
        end_reason=session.get("end_reason"),
        metrics_source=str(path),
        metrics_scope="main_agent_session",
        metrics_warnings=warnings,
    )
    for field in ("input_tokens", "output_tokens", "reasoning_tokens", "cache_read_tokens", "cache_write_tokens"):
        result[field] = _counter(session, field, warnings)
    result["api_calls"] = _counter(session, "api_call_count", warnings)
    result["reported_tool_calls"] = _counter(session, "tool_call_count", warnings)
    if result["input_tokens"] is not None and result["output_tokens"] is not None:
        result["uncached_input_output_tokens"] = result["input_tokens"] + result["output_tokens"]
    if all(result[field] is not None for field in ("input_tokens", "cache_read_tokens", "cache_write_tokens")):
        result["prompt_tokens"] = result["input_tokens"] + result["cache_read_tokens"] + result["cache_write_tokens"]
        if result["output_tokens"] is not None:
            result["total_tokens"] = result["prompt_tokens"] + result["output_tokens"]
    if result["reasoning_tokens"] == 0:
        warnings.append("reasoning_tokens is reported as zero; this does not establish that reasoning was disabled or metered")
    if result["total_tokens"] == 0 and result["api_calls"]:
        warnings.append("Token counters are reported as zero despite API calls; provider usage availability is not verified")
    if session.get("parent_session_id"):
        warnings.append("This session has a parent; reported usage may include a resumed history")

    started, ended = _timestamp(session.get("started_at")), _timestamp(session.get("ended_at"))
    if started is not None and ended is not None and ended >= started:
        result["session_elapsed_seconds"] = ended - started
    else:
        warnings.append("Session duration is unavailable: valid started_at and ended_at timestamps are required")

    messages = session.get("messages")
    if not isinstance(messages, list) or any(not isinstance(item, dict) for item in messages):
        warnings.append("Session messages are unavailable or malformed; observed turn/tool counts are unavailable")
        return result
    result.update(
        assistant_turns=0, tool_iterations=0, tool_calls=0, user_messages=0,
        active_assistant_turns=0, inactive_assistant_turns=0,
        active_tool_calls=0, inactive_tool_calls=0, inactive_message_count=0,
        observed_message_count=0,
    )
    invalid_tool_calls = False
    for index, message in enumerate(messages):
        inactive = _is_inactive(message)
        if inactive:
            result["inactive_message_count"] += 1
        if message.get("observed") in (True, 1, "1", "true", "True"):
            result["observed_message_count"] += 1
        if message.get("role") == "user":
            result["user_messages"] += 1
        if message.get("role") != "assistant":
            continue
        result["assistant_turns"] += 1
        result["inactive_assistant_turns" if inactive else "active_assistant_turns"] += 1
        calls = _tool_calls(message, index, warnings)
        if calls is None:
            invalid_tool_calls = True
            continue
        if calls:
            result["tool_iterations"] += 1
            result["tool_calls"] += len(calls)
            result["inactive_tool_calls" if inactive else "active_tool_calls"] += len(calls)
    if invalid_tool_calls:
        for key in ("tool_calls", "tool_iterations", "active_tool_calls", "inactive_tool_calls"):
            result[key] = None
    if any(message.get("active") is None for message in messages):
        warnings.append("Not every message has an active flag; unmarked messages are included in active counts")
    if result["inactive_message_count"]:
        warnings.append("Observed work counts include inactive/rewound messages; active counts describe retained history only")
    if result["reported_tool_calls"] is not None and result["tool_calls"] is not None and result["reported_tool_calls"] != result["tool_calls"]:
        warnings.append("Reported tool_call_count differs from calls in exported assistant messages")
    return result


def _attempt_sessions(path: Path, source: Path) -> list[dict[str, Any]]:
    """Select latest snapshots and reject unrelated/missing session lineages."""
    latest: dict[str, dict[str, Any]] = {}
    for session in _read_sessions(path):
        identity = session.get("id", session.get("session_id"))
        if not isinstance(identity, str) or not identity:
            raise ValueError("Every attempt session must have a nonempty string ID")
        latest[identity] = session
    roots = [identity for identity, session in latest.items() if session.get("parent_session_id") is None]
    if len(roots) != 1:
        raise ValueError("Attempt export must contain one connected lineage with exactly one root")
    for identity, session in latest.items():
        seen: set[str] = set()
        current = identity
        while current != roots[0]:
            if current in seen:
                raise ValueError("Attempt session lineage contains a cycle")
            seen.add(current)
            parent = latest[current].get("parent_session_id")
            if not isinstance(parent, str) or parent not in latest:
                raise ValueError(f"Attempt export omits parent session {parent!r}")
            current = parent
        cwd = session.get("cwd")
        if cwd is not None and (not isinstance(cwd, str) or Path(cwd).resolve() != source.resolve()):
            raise ValueError(f"Session {identity} cwd does not match the attempt source")
    def lineage_depth(session: dict[str, Any]) -> int:
        depth, current = 0, session["id"]
        while current != roots[0]:
            current = latest[current]["parent_session_id"]
            depth += 1
        return depth
    return sorted(latest.values(), key=lambda session: (lineage_depth(session), _timestamp(session.get("started_at")) or 0, session["id"]))


def _canonical_totals(result: dict[str, Any]) -> None:
    for field in ("prompt_tokens", "total_tokens", "uncached_input_output_tokens"):
        result[field] = None
    if result.get("input_tokens") is not None and result.get("output_tokens") is not None:
        result["uncached_input_output_tokens"] = result["input_tokens"] + result["output_tokens"]
    if all(result.get(field) is not None for field in ("input_tokens", "cache_read_tokens", "cache_write_tokens")):
        result["prompt_tokens"] = result["input_tokens"] + result["cache_read_tokens"] + result["cache_write_tokens"]
        if result.get("output_tokens") is not None:
            result["total_tokens"] = result["prompt_tokens"] + result["output_tokens"]


def _database_usage(path: Path, session_ids: set[str], warnings: list[str]) -> dict[str, Any] | None:
    """Read additive per-model usage buckets; never add native counters to them."""
    fields = ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens", "reasoning_tokens", "api_call_count")
    try:
        with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as connection:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(session_model_usage)")}
            if not {"session_id", "task"}.issubset(columns):
                warnings.append("Usage database lacks the supported session_model_usage schema")
                return None
            identities = {row[0] for row in connection.execute("SELECT DISTINCT session_id FROM session_model_usage WHERE task = ''")}
            if not identities:
                warnings.append("Usage database has no main-agent usage rows")
                return None
            if not identities.issubset(session_ids):
                warnings.append("Usage database contains main-agent sessions outside the validated export lineage; usage is unavailable")
                return None
            sums = ", ".join(f"CASE WHEN COUNT({field}) = COUNT(*) THEN SUM({field}) ELSE NULL END" if field in columns else "NULL" for field in fields)
            row = connection.execute(f"SELECT {sums} FROM session_model_usage WHERE task = ''").fetchone()
    except (OSError, sqlite3.Error) as exc:
        warnings.append(f"Cannot read usage database: {exc}")
        return None
    return {field: _counter(dict(zip(fields, row)), field, warnings) for field in fields}


def _attempt_message_counts(sessions: list[dict[str, Any]], warnings: list[str]) -> dict[str, Any]:
    """Deduplicate copied history by Hermes occurrence UIDs, not provider IDs."""
    count_fields = ("assistant_turns", "tool_iterations", "tool_calls", "user_messages", "active_assistant_turns", "inactive_assistant_turns", "active_tool_calls", "inactive_tool_calls", "inactive_message_count", "observed_message_count")
    messages: dict[str, dict[str, Any]] = {}
    for session in sessions:
        rows = session.get("messages")
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            warnings.append("Compressed attempt messages are unavailable or malformed; work counts are unknown")
            return dict.fromkeys(count_fields)
        for row in rows:
            uid = row.get("message_uid")
            if not isinstance(uid, str) or not uid:
                warnings.append("Multi-session export has missing message occurrence UIDs; work counts are unknown")
                return dict.fromkeys(count_fields)
            messages[uid] = row
    counts = dict.fromkeys(count_fields, 0)
    occurrences: dict[str, bool] = {}
    for index, message in enumerate(messages.values()):
        inactive = _is_inactive(message)
        counts["inactive_message_count"] += int(inactive)
        counts["observed_message_count"] += int(message.get("observed") in (True, 1, "1", "true", "True"))
        counts["user_messages"] += int(message.get("role") == "user")
        if message.get("role") != "assistant":
            continue
        counts["assistant_turns"] += 1
        counts["inactive_assistant_turns" if inactive else "active_assistant_turns"] += 1
        calls = _tool_calls(message, index, warnings)
        if calls is None:
            return dict.fromkeys(count_fields)
        counts["tool_iterations"] += int(bool(calls))
        uid_map = message.get("tool_call_uids")
        if isinstance(uid_map, str):
            try:
                uid_map = json.loads(uid_map)
            except json.JSONDecodeError:
                uid_map = None
        per_id_indices: dict[str, int] = {}
        for call in calls:
            provider_id = call.get("id", call.get("call_id"))
            if not isinstance(provider_id, str):
                warnings.append("Multi-session export has a tool call without a usable provider ID; work counts are unknown")
                return dict.fromkeys(count_fields)
            uids = uid_map.get(provider_id) if isinstance(uid_map, dict) else None
            occurrence_index = per_id_indices.get(provider_id, 0)
            per_id_indices[provider_id] = occurrence_index + 1
            if isinstance(uids, list):
                uid = uids[occurrence_index] if occurrence_index < len(uids) else None
            else:
                uid = uids if occurrence_index == 0 else None
            if not isinstance(uid, str) or not uid:
                warnings.append("Multi-session export has missing tool occurrence UIDs; work counts are unknown")
                return dict.fromkeys(count_fields)
            occurrences[uid] = inactive
    counts["tool_calls"] = len(occurrences)
    counts["inactive_tool_calls"] = sum(occurrences.values())
    counts["active_tool_calls"] = counts["tool_calls"] - counts["inactive_tool_calls"]
    if any(message.get("active") is None for message in messages.values()):
        warnings.append("Not every message has an active flag; unmarked messages are included in active counts")
    return counts


def extract_attempt_metrics(export_path: Path, source: Path, usage_db: Path | None = None, session_id: str | None = None) -> dict[str, Any]:
    """Measure one fresh agent attempt across context-compression child sessions.

    All export sessions must share one complete lineage and the requested source
    cwd. SQLite task='' usage buckets are additive deltas and replace cumulative
    export counters. Without those buckets, multi-session token totals are unknown.
    Copied message/tool history is deduplicated using Hermes occurrence UIDs.
    """
    export_path, source = Path(export_path), Path(source)
    sessions = _attempt_sessions(export_path, source)
    by_id = {session["id"]: session for session in sessions}
    if session_id is not None and session_id not in by_id:
        raise ValueError(f"Session {session_id!r} was not found in the attempt export")
    parents = {session.get("parent_session_id") for session in sessions}
    leaves = [session for session in sessions if session["id"] not in parents]
    chosen = by_id[session_id] if session_id else max(leaves, key=lambda session: (_timestamp(session.get("ended_at")) or _timestamp(session.get("started_at")) or 0, session["id"]))
    result = extract_session_metrics(export_path, chosen["id"])
    warnings = result["metrics_warnings"]
    result.update(metrics_scope="main_agent_attempt", session_ids=[session["id"] for session in sessions])
    if any(session.get("cwd") is None for session in sessions):
        warnings.append("One or more sessions omit cwd; source-directory validation is incomplete")
    if len(sessions) > 1:
        warnings.append("Attempt contains compression/continuation child sessions; cumulative export token counters are not additive")
        result.update(_attempt_message_counts(sessions, warnings))
        for field in ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens", "reasoning_tokens"):
            result[field] = None
        result["usage_source"] = "unavailable_without_additive_usage_database"
    if session_id is None and len(sessions) > 1:
        values = [_counter(session, "api_call_count", warnings) for session in sessions]
        result["api_calls"] = max((value for value in values if value is not None), default=None)
        warnings.append("api_calls is the maximum reported session counter; compression may clone cumulative counters")
    database_usage = _database_usage(Path(usage_db), set(by_id), warnings) if usage_db is not None else None
    if database_usage is not None:
        for field in ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens", "reasoning_tokens"):
            result[field] = database_usage[field]
        result["api_calls_with_usage"] = database_usage["api_call_count"]
        result["usage_source"] = f"{usage_db}:session_model_usage task='' additive buckets"
        if result["api_calls"] is not None and result["api_calls_with_usage"] is not None and result["api_calls_with_usage"] < result["api_calls"]:
            warnings.append("Usage database covers fewer API calls than the reported counter; usage may be partial or provider responses may omit usage")
    _canonical_totals(result)
    starts = [_timestamp(session.get("started_at")) for session in sessions]
    ends = [_timestamp(session.get("ended_at")) for session in sessions]
    known_starts, known_ends = [value for value in starts if value is not None], [value for value in ends if value is not None]
    result["session_elapsed_seconds"] = max(known_ends) - min(known_starts) if known_starts and known_ends and max(known_ends) >= min(known_starts) else None
    if any(value is None for value in starts + ends):
        warnings.append("Attempt timing has missing session timestamps; duration uses known boundaries only")
    warnings[:] = [warning for warning in warnings if "reasoning_tokens is reported as zero" not in warning]
    if result["reasoning_tokens"] == 0:
        warnings.append("reasoning_tokens is reported as zero; this does not establish that reasoning was disabled or metered")
    return result


def _flatten(record: dict[str, Any]) -> dict[str, Any]:
    row = {key: value for key, value in record.items() if key != "metrics"}
    metrics = record.get("metrics")
    if isinstance(metrics, dict):
        for key, value in metrics.items():
            row.setdefault(key, value)
    elif "metrics" in record:
        row["metrics"] = metrics
    return row


def _cell(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value


def _markdown_cell(value: Any) -> str:
    if value is None or value == "":
        return "unknown"
    return str(value).replace("|", "\\|").replace("\n", " ")


def _numeric(record: dict[str, Any], field: str) -> float | None:
    value = record.get(field)
    if isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0:
        return float(value)
    return None


def _average(records: list[dict[str, Any]], field: str, integer: bool = False) -> str:
    known = [value for record in records if (value := _numeric(record, field)) is not None]
    if not known:
        return "unknown (0 recorded)"
    number = f"{mean(known):.0f}" if integer else f"{mean(known):.2f}"
    return f"{number} ({len(known)}/{len(records)} recorded)"


def _summary(rows: list[dict[str, Any]]) -> str:
    lines = ["# Coding evaluation results", "", f"Attempts recorded: **{len(rows)}**.", "",
             "Archived incomplete attempts and current run results are all retained; retries count as separate attempts.", "",
             "Native Hermes session token metrics cover the main agent session. Auxiliary-task usage is preserved separately when recorded and is not included in these token means.", "",
             "Functional verdicts come from the acceptance checker. Process outcomes are recorded separately; a budget stop can still produce a passing patch.", "",
             "Effort is the requested setting. Verified effort counts only runs whose recorded Hermes configuration was confirmed; it does not establish that the serving backend honored the setting.", "",
             "Pass rates use only PASS and FAIL verdicts. Other verdicts remain visible. Hermes token totals are uncached input plus cache reads plus cache writes plus output. Reasoning is an output detail and is not added twice. Missing counters make totals unknown.", ""]
    if not rows:
        lines.append("No run results have been recorded yet.")
        return "\n".join(lines) + "\n"
    lines.extend([
        "| Case | Budget | Effort | Max turns | Max seconds | Attempts | Verified effort | PASS | FAIL | Other | Pass rate | Mean elapsed seconds | Mean total tokens | Mean tool iterations |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |",
    ])
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in rows:
        key = tuple(_cell(row.get(field)) for field in ("case_id", "budget_name", "reasoning_effort", "max_turns", "max_seconds"))
        groups.setdefault(key, []).append(row)
    for key in sorted(groups, key=lambda item: tuple(str(value) for value in item)):
        group = groups[key]
        passed = sum(str(item.get("verdict", "")).upper() == "PASS" for item in group)
        failed = sum(str(item.get("verdict", "")).upper() == "FAIL" for item in group)
        scored = passed + failed
        rate = f"{100 * passed / scored:.1f}% ({passed}/{scored})" if scored else "unknown (0 scored)"
        verified = sum(item.get("reasoning_verified") is True for item in group)
        values = [*key, len(group), f"{verified}/{len(group)}", passed, failed, len(group) - scored, rate,
                  _average(group, "elapsed_seconds"), _average(group, "total_tokens", True),
                  _average(group, "tool_iterations")]
        lines.append("| " + " | ".join(_markdown_cell(value) for value in values) + " |")
    lines.extend(["", "| Functional verdict | Attempts |", "| --- | ---: |"])
    for field in ("verdict", "process_status"):
        if field == "process_status":
            lines.extend(["", "| Process outcome | Attempts |", "| --- | ---: |"])
        counts: dict[str, int] = {}
        for row in rows:
            status = str(row.get(field) or "UNKNOWN")
            counts[status] = counts.get(status, 0) + 1
        for status, count in sorted(counts.items()):
            lines.append(f"| {_markdown_cell(status)} | {count} |")
    errors = [row for row in rows if row.get("error")]
    if errors:
        lines.extend(["", "| Run | Error |", "| --- | --- |"])
        for row in errors:
            lines.append(f"| {_markdown_cell(row.get('run_id'))} | {_markdown_cell(row['error'])} |")
    lines.extend(["", "Raw records are preserved in `results.jsonl`; `results.csv` includes configuration, metrics, errors, and any additional recorded fields."])
    return "\n".join(lines) + "\n"


def _atomic_write(path: Path, content: str) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def write_reports(batch_dir: Path) -> None:
    """Rebuild reports from current and archived attempts without deduplication.

    Reads runs/*/result.json and incomplete/*/result.json. Auxiliary counters
    supplied by the runner remain separate from main-session usage.
    """
    batch_dir = Path(batch_dir)
    batch_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    paths = [*(batch_dir / "runs").glob("*/result.json"),
             *(batch_dir / "incomplete").glob("*/result.json")]
    for path in sorted(paths):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(record, dict):
                raise ValueError("Run result must be a JSON object")
        except (OSError, ValueError) as exc:
            record = {"run_id": path.parent.name, "verdict": "UNKNOWN", "process_status": "report_error", "error": f"Cannot read {path}: {exc}"}
        records.append(record)
    rows = [_flatten(record) for record in records]
    fields = list(dict.fromkeys(REPORT_FIELDS))
    fields.extend(sorted({key for row in rows for key in row} - set(fields)))
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    writer.writerows({key: _cell(value) for key, value in row.items()} for row in rows)
    _atomic_write(batch_dir / "results.jsonl", "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records))
    _atomic_write(batch_dir / "results.csv", buffer.getvalue())
    _atomic_write(batch_dir / "summary.md", _summary(rows))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    metrics = commands.add_parser("metrics", help="Extract usage/turn metrics from an existing session export")
    metrics.add_argument("export_path", type=Path)
    metrics.add_argument("--session-id")
    metrics.add_argument("--source", type=Path, help="Validate a complete fresh attempt across compression sessions")
    metrics.add_argument("--usage-db", type=Path, help="Read additive usage from the attempt fresh-home SQLite database; requires --source")
    report = commands.add_parser("report", help="Rebuild JSONL, CSV, and Markdown reports from existing run results")
    report.add_argument("batch_dir", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "metrics":
            if args.usage_db is not None and args.source is None:
                parser.error("--usage-db requires --source")
            extracted = extract_attempt_metrics(args.export_path, args.source, args.usage_db, args.session_id) if args.source is not None else extract_session_metrics(args.export_path, args.session_id)
            print(json.dumps(extracted, indent=2, ensure_ascii=False))
        else:
            write_reports(args.batch_dir)
            print(f"Reports written to {args.batch_dir}")
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
