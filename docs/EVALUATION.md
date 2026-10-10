# Automated coding evaluation

The framework runs the pinned coding cases through Hermes, grades the resulting source, and records usage and timing. It uses the existing local Muse Glimmer server on the 5090 machine. Runs are sequential; the wrapper uses Python's standard library, Git, pip, and the installed Hermes CLI.

The defaults in [config/evaluation.json](../config/evaluation.json) produce **48 runs**: four cases × three budgets × four reasoning settings × one repeat. The order is shuffled reproducibly with seed 42.

| Budget | Maximum tool-calling iterations | Maximum agent seconds |
| --- | ---: | ---: |
| small | 15 | 300 |
| medium | 30 | 600 |
| large | 60 | 1200 |

The requested reasoning settings are `low`, `medium`, `high`, and `xhigh`. The default matrix allows **9 hours 20 minutes of agent execution**, plus preparation, individual environment setup, grading, session export, and termination grace. This is a ceiling, not an estimated completion time. One repeat is a useful first experiment; it does not measure variance.

## Prepare the machine

Use Python 3.12 or later, Git, pip, and the working Hermes installation used for the individual case runs. The Python installation must support `venv`. Start Muse Glimmer before launching the evaluation; the wrapper checks Hermes flags and the local server's model list.

On the 5090 machine, normalize the existing `CASE_PYTHON` variable to an absolute interpreter path:

```bash
cd /workspace/muse-glimmer-field-notes
: "${CASE_PYTHON:?Set CASE_PYTHON to your existing Python 3.12+ interpreter}"
CASE_PYTHON="$("$CASE_PYTHON" -c 'import sys; print(sys.executable)')"
export CASE_PYTHON
"$CASE_PYTHON" --version
hermes --version
```

Review these fields in `config/evaluation.json` before starting a batch:

| Field | Default | What to check |
| --- | --- | --- |
| `base_url` | `http://127.0.0.1:8081/v1` | Match the running local server; only loopback HTTP endpoints are accepted. |
| `model` | `muse-glimmer` | Match the alias returned by `/v1/models`. |
| `context_length` | `131072` | Match the server's context available to one slot. |
| `sampling` | temperature `1.0`, top_p `0.95`, top_k `64` | Keep sampling fixed across the matrix. |
| `api_key_env` | `GLIMMER_API_KEY` | Export the existing local server key when authentication is enabled. |
| `hermes_command` | `["hermes"]` | Use an argv list; an absolute CLI path can be supplied if needed. |

If the server requires authentication, set `GLIMMER_API_KEY` in the shell from your existing local key before launching. The configuration stores the environment variable's name, not its value. The runner does not copy your usual Hermes credentials or memory. A server without authentication uses a nonempty SDK placeholder automatically.

Check `n_ctx_slot` in the llama.cpp startup log. Context is divided between concurrent slots: a server configured with `-c 131072 -np 4` provides 32768 tokens per slot. Set `context_length` accordingly, or serve one slot if you want the whole 131072 context for this sequential experiment. [Meta's llama.cpp recipe](https://github.com/meta-models/meta-oss-cookbook/blob/main/inference-server/llama-cpp.md) describes this constraint.

The default sampling follows [Meta's prompting guide](https://dev.meta.ai/docs/muse-glimmer/prompting). The runner also requests `parallel_tool_calls: false`, matching the model's documented single-call behavior.

## Inspect and smoke-test the matrix

Print the default matrix without making model calls, downloading files, or creating a batch:

```bash
"$CASE_PYTHON" scripts/evaluate_coding.py --dry-run
```

Run one short smoke test before the full matrix:

```bash
"$CASE_PYTHON" -u scripts/evaluate_coding.py \
  --cases C02 --efforts low --budgets small
```

The script prints `Batch: /workspace/muse-glimmer-field-notes/.runs/evaluation/<timestamp>`. Check that batch's `runs/C02-small-low-r01/result.json`, `check.log`, and `transcript.log` before committing to the full run. A short budget may produce a functional failure; setup errors, missing model access, or missing usage need investigation.

Use `--cases`, `--efforts`, `--budgets`, and `--repeats` to select a smaller matrix. For example, `--cases C01 C03 --efforts medium high --budgets medium --repeats 2` creates eight runs. Edit `budgets` in the JSON file to change iteration and time limits, or supply a separate configuration with `--config /absolute/path/evaluation.json`. Limits apply to tool-calling iterations and wall-clock time; token expenditure is recorded rather than capped by this wrapper.

## Run the full evaluation overnight

Optional preparation verifies each case's failing base and passing reference, freezes the source/prompt/checker inputs, and downloads test wheels. It does not invoke a model:

```bash
"$CASE_PYTHON" -u scripts/evaluate_coding.py --prepare-only
```

To run that prepared batch, set `EVAL_BATCH` to its printed absolute path:

```bash
EVAL_BATCH=/workspace/muse-glimmer-field-notes/.runs/evaluation/REPLACE_WITH_PRINTED_TIMESTAMP
"$CASE_PYTHON" -u scripts/evaluate_coding.py --resume "$EVAL_BATCH"
```

For an unattended launch directly from the default configuration, run this single line from the repository on the 5090:

```bash
git pull --ff-only && bash scripts/run_evaluation.sh
```

[scripts/run_evaluation.sh](../scripts/run_evaluation.sh) resolves the checkout from its own location and finds Python 3.12+ automatically, preferring a usable `CASE_PYTHON`. A stale interpreter path from a deleted `.runs/` directory falls back to an installed Python. It checks the interpreter's `venv`/`pip` imports and validates the matrix before detaching the runner. The runner then checks Hermes and the server; inspect the log for setup failures.

The launcher uses the configured key environment variable, then `GLIMMER_API_KEY` or `glimmerapikey` if already set. Otherwise it prompts once without displaying the key; press Enter only for a server without authentication. For a launch without a terminal, export the key first, or explicitly set `GLIMMER_API_KEY=local-no-auth` for a server without authentication. Credentials are passed through the environment. Resume reads the key-variable name from the batch's frozen configuration.

The launcher recreates `.runs/`, preserves previous launch logs, writes `.runs/evaluation-launch.pid`, and refuses to start while that recorded process is alive. Once it prints the background PID, you can disconnect from SSH. `.runs/evaluation-launch.log` links to the newest timestamped launch log; it records the batch path and progress, and each attempt has its own transcript. Monitor with:

```bash
tail -f .runs/evaluation-launch.log
```

To launch a prepared or interrupted batch in the background, pass the existing runner's options:

```bash
bash scripts/run_evaluation.sh --resume "$EVAL_BATCH"
```

Other options are forwarded unchanged, for example `bash scripts/run_evaluation.sh --cases C02 --efforts low --budgets small`. `--dry-run` and `--help` stay in the foreground and never prompt for a key. The launcher uses `config/evaluation.json` by default; with the checked-in configuration it runs all four cases, four efforts and three budgets once.

Only one supervisor should run against the GPU at a time. The launcher's PID guard covers starts through this checkout's Bash script. Direct Python launches bypass it; the Python batch lock prevents two supervisors from rewriting the same batch. If a launcher is killed before it releases its short startup lock, verify that it has stopped before removing `.runs/.evaluation-launch-lock` and retrying.

A recycled PID or an unreaped container process can also leave a stale `.runs/evaluation-launch.pid` that blocks a restart. Remove that PID file only after confirming the previous evaluation has stopped.

## Resume and preserve results

```bash
"$CASE_PYTHON" -u scripts/evaluate_coding.py --resume "$EVAL_BATCH"
```

Resume uses the batch's frozen configuration and job order. Case/effort/budget/repeat filters cannot be changed while resuming. Frozen inputs and dependency wheel hashes are checked again.

Every job with `result.json` is preserved, including failed and interrupted jobs. Resume does not retry a completed failure. Use a new batch to repeat completed work. A hard interruption that leaves an unfinished attempt directory is archived under `incomplete/` before a fresh infrastructure retry; reports retain both attempts. An interrupted supervisor's dead-PID lock is recovered automatically on the same host. A lock owned by a live PID or another host stops the launch.

## What each attempt does

Each job starts from the pinned broken base, with a new source copy, new virtual environment, and new Hermes home and session database. Memory, profile injection, and preloaded rules are disabled. The source receives one synthetic Git commit so `git diff` describes that case's edits; upstream history and reference revisions are absent from the agent source.

The framework caches `pytest==9.0.2`, `flit_core==3.12.0`, and resolved dependency wheels once per batch. Individual venvs install from this wheelhouse offline. An editable installation points to that attempt's source and supplies Click distribution metadata. The framework checks that the selected upstream tests collect before starting the agent timer.

| Case | Focused upstream test selection |
| --- | --- |
| C01 | `tests/test_options.py -k envvar` |
| C02 | `tests/test_utils/test_make_default_short_help.py` |
| C03 | `tests/test_requirements.py` |
| C04 | `tests/test_metadata.py -k license_files` |

This setup supports these focused selections. Packaging's whole test suite imports additional packages such as `hypothesis`, `pretend`, and `tomli_w`; they are not installed by this lightweight framework.

Hermes runs with `--max-turns`, `--run-budget`, terminal/file tools, and a prompt instructing it to remain in its source directory. The supervisor also applies a wall-clock timeout, requests termination of the process group, and allows up to five seconds before forceful termination. It then attempts to export the fresh home's sessions and grade the partial source even if Hermes stopped at its budget.

The trusted acceptance checker runs with the framework interpreter and `-B -I`, outside the agent's venv. Its checksum is checked before grading. Checker exit `0` means `PASS`, `1` means `FAIL`, and `2` means `SETUP_ERROR`; timeouts and unexpected checker exits produce `CHECK_ERROR`. Hermes process status is recorded separately. A budget stop can therefore still have a passing patch.

Focused upstream pytest results are additional evidence, not the acceptance verdict. C02 has an old sentence-boundary fixture that contradicts the requested lowercase-following-word behavior: a correct `123 567...` result can fail that fixture's old `123 567 9.` expectation. Keep the pytest failure visible without automatically turning an acceptance pass into a failure.

The backend remains `local`. A fresh home, new Git baseline, and directory instructions improve repeatability but do not enforce filesystem or network isolation. The agent can technically reach other host files; each record states `filesystem_isolation: not_enforced` and `network_isolation: not_enforced`.

## Reasoning configuration and its evidence

Each run gets a generated named provider, `glimmer-eval`, with a Chat Completions transport. The selected effort is written to both Hermes's `agent.reasoning_effort` and:

```json
{
  "extra_body": {
    "chat_template_kwargs": {"reasoning_strength": "low"}
  }
}
```

The value changes to `medium`, `high`, or `xhigh` for the other matrix conditions. [Meta's prompting guide](https://dev.meta.ai/docs/muse-glimmer/prompting) documents these four template strengths. [Meta's llama.cpp recipe](https://github.com/meta-models/meta-oss-cookbook/blob/main/inference-server/llama-cpp.md) specifies `chat_template_kwargs.reasoning_strength` for this server; the generic OpenAI `reasoning_effort` spelling alone is insufficient here.

The named-provider path copies `extra_body` into the runtime in the inspected [Hermes custom-provider source at 46d7718a](https://github.com/NousResearch/hermes-agent/blob/46d7718a52ff33accb15dc0501736fbdb6833cab/hermes_cli/runtime_provider_custom.py). This verifies the configuration mechanism in that source version. The wrapper records the requested setting and generated configuration; it does not independently capture the HTTP request or prove the serving backend honored the setting. Read `reasoning_verified` and `reasoning_verification` with that limit in mind, and retain the installed Hermes version log.

## Usage, turns, and timing

Recorded counters come from Hermes exports and, when available, its native usage database. Missing or invalid counters stay `null` in JSON, blank in CSV, and `unknown` in the Markdown report. The framework does not estimate token counts from characters or replace missing usage with zero.

| Metric | Definition |
| --- | --- |
| `input_tokens` | Hermes's canonical uncached input counter. |
| `cache_read_tokens`, `cache_write_tokens` | Native cache counters, kept separate. |
| `prompt_tokens` | `input_tokens + cache_read_tokens + cache_write_tokens`. |
| `output_tokens` | Native completion/output counter. |
| `total_tokens` | `prompt_tokens + output_tokens`; requires all component counters. |
| `reasoning_tokens` | An output detail; it is not added to `total_tokens` again. |
| `api_calls` | Reported native main-agent API-call counter, which can differ from message counts. |
| `api_calls_with_usage` | Main-agent API calls represented by additive usage database rows; can be lower if usage is unavailable. |
| `assistant_turns` | Observed assistant messages; includes a final response if exported. |
| `tool_iterations` | Assistant messages containing at least one tool call. |
| `tool_calls` | Calls in assistant `tool_calls` arrays; tool result messages are not counted again. |
| `elapsed_seconds` | Supervisor-measured agent-process wall time, including termination grace. |
| `setup_seconds` | Individual source, Git, venv, dependency, and test-collection setup. |
| `check_seconds` | Acceptance-check execution time. |
| `total_seconds` | Whole attempt time, including setup and evidence collection. |
| `session_elapsed_seconds` | Duration between the native session timestamps when available. |

The runner exports every session in the fresh Hermes home. Automatic context compression can create child sessions, so it validates one connected lineage and checks its source directory. Main-agent token totals use read-only sums of additive `session_model_usage` buckets whose `task` is empty, across that attempt's database. These replace cumulative export counters; exported session totals must not be summed together. Multi-session token totals stay unknown if usable additive database usage is absent.

Copied context is counted once using stable message and tool occurrence UIDs. Repeated provider tool-call IDs alone are not used to deduplicate work. If a multi-session export lacks the needed occurrence IDs, work counts stay unknown. `session_ids`, `usage_source`, and `metrics_warnings` preserve the provenance and limits of these calculations.

Auxiliary tasks such as approval or compression can also spend tokens. The runner retains auxiliary `session_model_usage` rows with a nonempty `task` separately as `auxiliary_usage` and `auxiliary_*` counters. `all_recorded_total_tokens` combines main and auxiliary totals only when both are known. Markdown token means use the main total; inspect the separate auxiliary columns when reporting overall recorded expenditure. The accounting definitions follow the pinned [Hermes usage normalization](https://github.com/NousResearch/hermes-agent/blob/46d7718a52ff33accb15dc0501736fbdb6833cab/agent/usage_pricing.py) and [native usage persistence](https://github.com/NousResearch/hermes-agent/blob/46d7718a52ff33accb15dc0501736fbdb6833cab/hermes_state_usage.py).

Observed work counts include inactive or rewound messages because the work already happened. Active counts are also recorded for examining retained context. A native zero reasoning counter does not prove reasoning was disabled or separately metered. A run with model calls and zero token counters receives a warning; check provider usage support before treating zeros as measured consumption.

After a timeout or process interruption, `metrics_status: partial_after_termination` marks counters that may omit pending responses or queued usage. Compare `api_calls` with `api_calls_with_usage` and inspect warnings: providers can omit usage even on otherwise completed calls. Available counters represent recorded consumption, not a promise that every request was metered.

The Markdown summary groups attempts by case, budget, and requested effort. Pass rates use only `PASS` and `FAIL`; infrastructure and unknown outcomes remain visible. Means show how many attempts supplied each metric. These four selected cases are a small blog experiment, so retain all outcomes and avoid presenting one repeat as a broad model benchmark.

## Artifacts and report rebuilding

Batch artifacts live under `.runs/evaluation/<timestamp>/` and are ignored by Git:

```text
config.json, jobs.json, environment.json
hermes-help.log, hermes-version.log, server-models.json
prepare-Cxx.log, download-wheels.log
inputs/Cxx/{base/,case.json,prompt.md,check.py,manifest.json}
wheels/, wheel-hashes.json, prepared.json
runs/Cxx-budget-effort-r01/
  source/                    # edited source, .venv, and synthetic .git
  hermes-home/               # isolated Hermes config and native database
  prompt.md, command.json
  dependencies.txt, test-collection.log, setup logs
  transcript.log, export.log, session.jsonl
  acceptance-check.py, check.log, upstream-check.log
  source.patch, source-changes.json
  result.json
incomplete/                  # preserved unfinished attempts, if any
results.jsonl, results.csv, summary.md
```

Some artifacts are absent if their stage failed or was interrupted. Preserve the whole batch directory for analysis; the reports contain paths to its evidence. Commit a reviewed summary to the shared repository when ready to write the blog.

Rebuild reports from existing records without model calls or rerunning cases:

```bash
"$CASE_PYTHON" scripts/eval_metrics.py report "$EVAL_BATCH"
```

Inspect complete-attempt metrics, including compression sessions and additive usage:

```bash
"$CASE_PYTHON" scripts/eval_metrics.py metrics \
  "$EVAL_BATCH/runs/C02-small-low-r01/session.jsonl" \
  --source "$EVAL_BATCH/runs/C02-small-low-r01/source" \
  --usage-db "$EVAL_BATCH/runs/C02-small-low-r01/hermes-home/state.db"
```

For a standalone single-session export, omit `--source` and `--usage-db`. If an export contains several sessions, `--session-id SESSION_ID` selects the session to inspect. The complete-attempt command still validates and accounts for the entire fresh-home lineage.

The report command reads current `runs/*/result.json` and archived `incomplete/*/result.json`, then rebuilds `results.jsonl`, `results.csv`, and `summary.md`. It preserves raw attempt records and does not deduplicate retries into a single success.
